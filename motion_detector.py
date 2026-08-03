import os
import urllib.request
import cv2
import mediapipe as mp
import datetime as dt
import time
import threading  # MODUL ZA RAD U POZADINSKIM NITIMA (Sprečava seckanje)

# Pretpostavljeni uvozi tvojih servisa
from blob_service import save_snapshot
from events_service import send_event


# ==============================================================================
# 1. HELPER FUNKCIJA ZA POZADINSKO SLANJE
# ==============================================================================

def send_event_async(event_type, data):
    """
    Pomoćna funkcija koja pokreće slanje eventa u zasebnoj pozadinskoj niti.
    Glavna petlja kamere ne čeka odgovor sa mreže, pa nema seckanja video strima.
    """
    thread = threading.Thread(target=send_event, args=(event_type, data), daemon=True)
    thread.start()


# ==============================================================================
# 2. PRIPREMA MODELA ZA DETEKCIJU LICA
# ==============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(SCRIPT_DIR, 'blaze_face_full_range.tflite')

if not os.path.exists(MODEL_PATH):
    print("Preuzimam MediaPipe Face Detector model...")
    url = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_full_range/float16/1/blaze_face_full_range.tflite"
    urllib.request.urlretrieve(url, MODEL_PATH)

BaseOptions = mp.tasks.BaseOptions
FaceDetector = mp.tasks.vision.FaceDetector
FaceDetectorOptions = mp.tasks.vision.FaceDetectorOptions
VisionRunningMode = mp.tasks.vision.RunningMode

options = FaceDetectorOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=VisionRunningMode.IMAGE,
    min_detection_confidence=0.5
)


# ==============================================================================
# 3. GLAVNA FUNKCIJA ZA NADZOR
# ==============================================================================

def detection(cap):
    poslednje_slanje_pokreta = None
    poslednje_slanje_lica = None

    print("Zagrevanje kamere u toku...")
    for _ in range(10):
        cap.read()
        time.sleep(0.1)

    ret, prev_clean_frame = cap.read()
    if not ret or prev_clean_frame is None:
        print("Kritična greška: Kamera nije poslala slikovni signal.")
        return

    print("Kamera je aktivna! Pritisnite 'q' za izlaz.")

    with FaceDetector.create_from_options(options) as detector:
        while cap.isOpened():
            ret, current_clean_frame = cap.read()
            if not ret or current_clean_frame is None:
                continue

            display_frame = current_clean_frame.copy()

            # ------------------------------------------------------------------
            # 1. DETEKCIJA POKRETA
            # ------------------------------------------------------------------
            diff = cv2.absdiff(prev_clean_frame, current_clean_frame)
            gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)
            _, thresh = cv2.threshold(blur, 20, 255, cv2.THRESH_BINARY)
            dilated = cv2.dilate(thresh, None, iterations=3)
            contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            motion_detected = False
            for contour in contours:
                if cv2.contourArea(contour) < 700:
                    continue
                motion_detected = True
                cv2.putText(display_frame, "Detektovan pokret!", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

            now = dt.datetime.now()
            if motion_detected:
                if poslednje_slanje_pokreta is None or (now - poslednje_slanje_pokreta).total_seconds() > 10:
                    data = {"vreme": str(now), "kamera": "main"}

                    # KLJUČNA IZMENA: Pozivamo asinhronu funkciju sa pozadinskom niti!
                    send_event_async("motion_detected", data)

                    poslednje_slanje_pokreta = now

            # ------------------------------------------------------------------
            # 2. DETEKCIJA LICA
            # ------------------------------------------------------------------
            rgb_frame = cv2.cvtColor(current_clean_frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            detection_result = detector.detect(mp_image)

            if len(detection_result.detections) > 0:
                if poslednje_slanje_lica is None or (now - poslednje_slanje_lica).total_seconds() > 8:
                    data = {"vreme": str(now), "kamera": "main"}

                    # KLJUČNA IZMENA: Pozivamo asinhronu funkciju sa pozadinskom niti!
                    send_event_async("face_detected", data)

                    # Ako u budućnosti koristiš save_snapshot i on usporava,
                    # možeš i njega prebaciti u nit:
                    # threading.Thread(target=save_snapshot, args=(current_clean_frame.copy(),), daemon=True).start()

                    poslednje_slanje_lica = now

                for detection in detection_result.detections:
                    bbox = detection.bounding_box
                    start_point = (bbox.origin_x, bbox.origin_y)
                    end_point = (bbox.origin_x + bbox.width, bbox.origin_y + bbox.height)
                    cv2.rectangle(display_frame, start_point, end_point, (0, 255, 0), 2)

            # ------------------------------------------------------------------
            # 3. PRIKAZ I OSVEŽAVANJE
            # ------------------------------------------------------------------
            cv2.imshow("Nadzor (Pokret + Lice)", display_frame)
            prev_clean_frame = current_clean_frame.copy()

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()