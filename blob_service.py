import os, uuid
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
def save_snapshot(frame):
    try:
        print("Azure blob storage qucikstart")
        connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')

    # Create the BlobServiceClient object
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        container_name = 'mvm_screenshots'
        container_client = blob_service_client.get_container_client()
        blob_service_client.upload_blob(data)
        

    except Exception as ex:
        print('Exception:')
        print(ex)