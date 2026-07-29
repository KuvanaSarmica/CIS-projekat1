import os
from azure.storage.blob import BlobServiceClient
import cv2
import datetime as dt

from dotenv import load_dotenv


def save_snapshot(frame):
    try:
        load_dotenv()
        print("Azure blob storage qucikstart")
        connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')

    # Create the BlobServiceClient object
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        _, screenshot = cv2.imencode('.jpg',frame)
        screenshot = screenshot.tobytes()
        blob_client = blob_service_client.get_blob_client(
            container=os.getenv('AZURE_CONTAINER_NAME'),
            blob = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".jpg"
        )
        blob_client.upload_blob(screenshot)
    except Exception as ex:
        print('Exception:')
        print(ex)