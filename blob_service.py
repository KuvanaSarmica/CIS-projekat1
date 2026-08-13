import os
import cv2
import datetime as dt
import logging
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential

from push_notification import send_face_detection_notification

# Učitavamo .env fajl samo jednom pri pokretanju modula
load_dotenv()

connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
container_name = os.getenv('AZURE_CONTAINER_NAME')
face_container = os.getenv('AZURE_FACE_CONTAINER_NAME')
vision_endpoint = os.getenv('AZURE_VISION_ENDPOINT')
vision_key = os.getenv('AZURE_VISION_KEY')

# Inicijalizujemo Azure Blob klijenta jednom na nivou modula
blob_service_client = None
if connect_str:
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    except Exception as e:
        print(f"[Blob Service Error] Greška pri povezivanju sa Azure-om: {e}")


def save_snapshot(frame):
    """
    Konvertuje frejm u JPG format u memoriji i šalje direktno na Azure Blob Storage.
    Ne pravi nikakve privremene fajlove na disku.
    """
    if not blob_service_client or not face_container:
        print("[Blob Service Error] Azure konekcija ili ime kontejnera nisu podešeni.")
        return

    try:
        # Generišemo naziv fajla na osnovu trenutnog vremena
        blob_name = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".jpg"

        # Pretvaramo OpenCV frejm u JPG bajtove u RAM memoriji
        _, jpg_bytes = cv2.imencode('.jpg', frame)

        if jpg_bytes is None or len(jpg_bytes) == 0:  # ← Dodaj ovo
            print("[Blob Service Error] Nije moguće konvertovati frame u JPG")
            return

        # Dobijamo blob klijenta za konkretan fajl
        blob_client = blob_service_client.get_blob_client(
            container=face_container,
            blob=blob_name
        )

        # Upload bajtova direktno na Azure Blob Storage
        blob_client.upload_blob(jpg_bytes.tobytes(), overwrite=True)
        print(f"[Blob Storage] Uspešno sačuvan snapshot: {blob_name}")

        # --- DODATO: Poziv Azure Computer Vision analize odmah nakon uploada ---
        if vision_endpoint and vision_key:
            analyze_image_with_cv(jpg_bytes.tobytes())

    except Exception as ex:
        print(f"[Blob Service Exception]: {ex}")


def analyze_image_with_cv(image_data: bytes):
    """Analizira bajtove slike i vraća listu tagova i detektovanih objekata."""
    tags = []
    objects = []

    if not vision_endpoint or not vision_key:
        return tags, objects

    try:
        client = ImageAnalysisClient(
            endpoint=vision_endpoint,
            credential=AzureKeyCredential(vision_key)
        )

        result = client.analyze(
            image_data=image_data,
            visual_features=[
                VisualFeatures.TAGS,
                VisualFeatures.OBJECTS,
            ],
        )

        if result.tags is not None:
            tags = [tag.name for tag in result.tags.list]

        if result.objects is not None:
            for obj in result.objects.list:
                if obj.tags:
                    objects.append(f"{obj.tags[0].name} ({obj.tags[0].confidence:.0%})")

    except Exception as e:
        print(f"[Computer Vision Error]: {e}")

    return tags, objects


def process_face_snapshot(frame, camera="main", timestamp=None):
    """
    1. Otprema snapshot na Azure Blob Storage
    2. Poziva Computer Vision i izdvaja tagove/objekte
    3. Šalje dekstop push notifikaciju sa rezultatima
    """
    if not blob_service_client or not face_container:
        print("[Blob Service Error] Azure konekcija ili ime kontejnera nisu podešeni.")
        return

    try:
        blob_name = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".jpg"
        _, jpg_bytes = cv2.imencode('.jpg', frame)

        if jpg_bytes is None or len(jpg_bytes) == 0:
            print("[Blob Service Error] Nije moguće konvertovati frame u JPG")
            return

        jpg_data = jpg_bytes.tobytes()

        # 1. Upload na Azure Blob Storage
        blob_client = blob_service_client.get_blob_client(
            container=face_container,
            blob=blob_name
        )
        blob_client.upload_blob(jpg_data, overwrite=True)
        print(f"[Blob Storage] Uspešno sačuvan snapshot: {blob_name}")

        # 2. Analiza slike
        tags, objects = analyze_image_with_cv(jpg_data)

        # 3. Slanje notifikacije sa detaljima
        send_face_detection_notification(
            camera=camera,
            timestamp=timestamp,
            tags=tags,
            objects=objects
        )

    except Exception as ex:
        print(f"[Process Snapshot Exception]: {ex}")

def upload_video(file_path):
    """
    Šalje video fajl sa lokalnog diska na Azure Blob Storage
    i briše ga sa diska nakon uspešnog slanja radi uštede memorije.
    """
    if not blob_service_client or not container_name:
        print("[Blob Service Error] Azure konekcija ili ime kontejnera nisu podešeni.")
        return

    if not os.path.exists(file_path):
        print(f"[Blob Service Error] Fajl ne postoji na putanji: {file_path}")
        return

    try:
        # Uzimamo samo ime fajla (npr. 'motion_2026-08-04_20-10-00.mp4')
        blob_name = os.path.basename(file_path)

        blob_client = blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )

        # Čitamo i strimujemo lokalni fajl na Azure Blob Storage
        with open(file_path, "rb") as video_data:
            blob_client.upload_blob(video_data, overwrite=True)

        print(f"[Blob Storage] Uspešno sačuvan video: {blob_name}")

        # Opciono: Brišemo lokalni video fajl nakon uploada da ne punimo disk

    except Exception as ex:
        print(f"[Blob Service Exception pri uploadu videa]: {ex}")

    finally:
        # <--- DODATO: Briše lokalni fajl uvek (i u slučaju prekida/greške)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"[Clean up] Obrisan lokalni video fajl: {file_path}")
