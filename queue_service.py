import os
from azure.storage.queue import QueueClient
from dotenv import load_dotenv
import datetime as dt
import json

def send_motion_events():
    try:
        load_dotenv()
        connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        queue_name = os.getenv('AZURE_QUEUE_NAME')

        queue_client = QueueClient.from_connection_string(connect_str, queue_name)

        poruka = {
            "vreme": str(dt.datetime.now()),
            "tip": "motion_detected",
            "kamera": "main"
        }

        queue_client.send_message(json.dumps(poruka))
        print(f"Poruka poslata u Queue: {poruka}")


    # Quickstart code goes here
    except Exception as ex:
        print('Exception:')
        print(ex)