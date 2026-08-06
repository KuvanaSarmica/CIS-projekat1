import os
import urllib.request
import cv2
import mediapipe as mp
import datetime as dt
import time
import threading
from events_service import send_event

from push_notification import send_face_detection_notification


from stream_capture import StreamCapture
from blob_service import save_snapshot
from blob_service import upload_video


# ==============================================================================
# 1. POMOCNA FUNKCIJA ZA ASINHRONO SLANJE EVENTA
# ==============================================================================

def send_event_async(event_type, data):
    """
    Pokrece slanje eventa u zasebnoj pozadinskoj niti.
    Na ovaj nacin glavna petlja kamere ne ceka odgovor sa mreze,
    pa nema seckanja video prikaza.
    """
    # daemon=True znaci da ce se nit automatski ugasiti kad se ugasi glavni program
    thread = threading.Thread(target=send_event, args=(event_type, data), daemon=True)
    thread.start()



def send_face_notification_async(camera, timestamp):
    thread = threading.Thread(
        target=send_face_detection_notification,
        args=(camera, timestamp),
        daemon=True
    )
    thread.start()



# ==============================================================================
# 2. PRIPREMA MEDIAPIPE MODELA ZA DETEKCIJU LICA
# ==============================================================================

# Odredjujemo folder u kome se nalazi ovaj fajl
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Putanja do modela koji MediaPipe koristi za detekciju lica
MODEL_PATH = os.path.join(SCRIPT_DIR, 'blaze_face_full_range.tflite')

# Ako model ne postoji lokalno, preuzimamo ga sa interneta
if not os.path.exists(MODEL_PATH):
    print("Preuzimam MediaPipe Face Detector model...")
    url = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_full_range/float16/1/blaze_face_full_range.tflite"
    urllib.request.urlretrieve(url, MODEL_PATH)

# Ucitavamo potrebne klase iz MediaPipe biblioteke
BaseOptions = mp.tasks.BaseOptions
FaceDetector = mp.tasks.vision.FaceDetector
FaceDetectorOptions = mp.tasks.vision.FaceDetectorOptions
VisionRunningMode = mp.tasks.vision.RunningMode

# Podesavamo opcije za detektor lica:
# model_asset_path -> koji model koristimo
# running_mode -> IMAGE znaci da analiziramo frejm po frejm
# min_detection_confidence -> minimalna sigurnost da bi detekcija bila validna (0.5 = 50%)
options = FaceDetectorOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=VisionRunningMode.IMAGE,
    min_detection_confidence=0.5
)


# ==============================================================================
# 3. GLAVNA FUNKCIJA ZA NADZOR
# ==============================================================================

def detection(cap,snimač):
    # Pamtimo vreme poslednjeg slanja eventa za pokret i lice
    # None znaci da jos nikad nismo slali event
    poslednje_slanje_pokreta = None
    poslednje_slanje_lica = None


    # Zagrevanje kamere - prvih 10 frejmova se ignorisu
    # jer kamera na pocetku moze davati lose slike
    print("Zagrevanje kamere u toku...")
    for _ in range(10):
        cap.read()
        time.sleep(0.1)

    # Citamo prvi frejm koji koristimo kao referencu za detekciju pokreta
    ret, prev_clean_frame = cap.read()
    if not ret or prev_clean_frame is None:
        print("Kriticna greska: Kamera nije poslala signal.")
        return

    print("Kamera je aktivna! Pritisnite 'q' za izlaz.")

    # Pokrecemo MediaPipe detektor lica
    with FaceDetector.create_from_options(options) as detector:
        while cap.isOpened():

            # Citamo novi frejm sa kamere
            ret, current_clean_frame = cap.read()
            if not ret or current_clean_frame is None:
                # Ako frejm nije procitan, preskacemo iteraciju
                continue
            snimač.add_frame(current_clean_frame)
            # Pravimo kopiju frejma na kojoj cemo crtati pravougaonike
            # Na ovaj nacin original ostaje cist za poređenje pokreta
            display_frame = current_clean_frame.copy()

            # ------------------------------------------------------------------
            # DETEKCIJA POKRETA
            # ------------------------------------------------------------------

            # Racunamo razliku izmedju trenutnog i prethodnog frejma
            # Gdje su pikseli razliciti, tam je doslo do pokreta
            diff = cv2.absdiff(prev_clean_frame, current_clean_frame)

            # Konvertujemo u sivo jer nam boja nije potrebna za detekciju pokreta
            gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

            # Zamagljujemo sliku da smanjimo sum i lazne alarme
            blur = cv2.GaussianBlur(gray, (5, 5), 0)

            # Pragovanje - pikseli ispod vrednosti 20 postaju crni (nema pokreta)
            # pikseli iznad postaju beli (ima pokreta)
            _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)

            # Sirimo bele oblasti da spojimo bliske konture
            dilated = cv2.dilate(thresh, None, iterations=3)

            # Trazimo konture - granice bijelih oblasti koje predstavljaju pokret
            contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            motion_detected = False
            for contour in contours:
                # Ignorisemo male konture - to je obicno sum a ne pravi pokret
                if cv2.contourArea(contour) < 700:
                    continue

                # Ako smo dosli ovde, detektovan je pravi pokret
                motion_detected = True

                # Ispisujemo tekst na display frejmu
                cv2.putText(display_frame, "Detektovan pokret!", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            # Uzimamo trenutno vreme - koristimo ga za timer i u eventu
            now = dt.datetime.now()

            if motion_detected:

                snimač.motion()
                if poslednje_slanje_pokreta is None or \
                        (now - poslednje_slanje_pokreta).total_seconds() > 10:
                    data = {
                        "vreme": str(now),
                        "kamera": "main"
                    }
                    send_event_async(
                        "motion_detected",
                        data
                    )
                    poslednje_slanje_pokreta = now

            # ------------------------------------------------------------------
            # DETEKCIJA LICA
            # ------------------------------------------------------------------

            # MediaPipe zahteva RGB format, a OpenCV koristi BGR
            # Zato konvertujemo pre analize
            rgb_frame = cv2.cvtColor(current_clean_frame, cv2.COLOR_BGR2RGB)

            # Pakujemo frejm u MediaPipe Image objekat
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

            # Pokrećemo detekciju lica na trenutnom frejmu
            detection_result = detector.detect(mp_image)

            # Ako je detektovano jedno ili vise lica
            if len(detection_result.detections) > 0:

                # Saljemo event samo ako je proslo vise od 8 sekundi od poslednjeg slanja
                if poslednje_slanje_lica is None or \
                        (now - poslednje_slanje_lica).total_seconds() > 5:

                    data = {"vreme": str(now), "kamera": "main"}

                    # Saljemo face_detected event asinhrono
                    send_event_async("face_detected", data)
                    send_face_notification_async(data["kamera"], data["vreme"])

                    threading.Thread(
                        target=save_snapshot,
                        args=(current_clean_frame,),
                        daemon=True
                    ).start()


                    # Pamtimo vreme slanja
                    poslednje_slanje_lica = now

                # Crtamo pravougaonik oko svakog detektovanog lica
                for detection in detection_result.detections:
                    bbox = detection.bounding_box

                    # Gornji levi ugao pravougaonika
                    start_point = (bbox.origin_x, bbox.origin_y)

                    # Donji desni ugao pravougaonika
                    end_point = (bbox.origin_x + bbox.width, bbox.origin_y + bbox.height)

                    # Crtamo zeleni pravougaonik oko lica
                    cv2.rectangle(display_frame, start_point, end_point, (0, 255, 0), 2)

            # Ako se snimanje završilo, spremi video
            if snimač.should_save():

                video_path = snimač.save_video()

                if video_path:
                    threading.Thread(
                        target=upload_video,
                        args=(video_path,),
                        daemon=True
                    ).start()


            # ------------------------------------------------------------------
            # PRIKAZ I OSVEZAVANJE
            # ------------------------------------------------------------------


            # Prikazujemo frejm sa svim nacrtanim elementima
            cv2.imshow("Nadzor (Pokret + Lice)", display_frame)

            # Azuriramo prethodni frejm za sledecu iteraciju detekcije pokreta
            # Koristimo cistи frejm bez nacranih elemenata
            prev_clean_frame = current_clean_frame.copy()

            # Cekamo 1ms na pritisak tastera - 'q' za izlaz
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    # Oslobadjamo kameru i zatvaramo sve prozore
    cap.release()
    cv2.destroyAllWindows()
