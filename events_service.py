import os
from azure.eventgrid import EventGridPublisherClient, EventGridEvent
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
import datetime as dt


def send_event(event_type: str, data: dict):
    """
    Šalje event na Azure Event Grid Topic.

    event_type: tip eventa, npr. "motion.detected" ili "face.detected"
    data: rečnik sa podacima o eventu, npr. vreme i naziv fajla
    """
    try:
        # Učitavamo .env fajl kako bismo dobili kredencijale
        load_dotenv()

        # Endpoint je URL adresa našeg Event Grid Topica na Azureu
        # Key je lozinka koja dokazuje da smo mi vlasnici tog Topica
        endpoint = os.getenv('EVENTGRID_TOPIC_ENDPOINT')
        key = os.getenv('EVENTGRID_TOPIC_KEY')

        # Kreiramo klijenta koji će komunicirati sa Event Grid Topicom
        # AzureKeyCredential pakuje naš key u format koji Azure razume
        client = EventGridPublisherClient(endpoint, AzureKeyCredential(key))

        # Kreiramo event objekat koji sadrži:
        # event_type → tip eventa, Event Grid ga koristi za rutiranje
        #              na odgovarajuće subscribere (Functions)
        # data → naši podaci koje šaljemo (vreme, naziv fajla itd.)
        # subject → putanja koja opisuje izvor eventa, korisna za filtriranje
        # data_version → verzija formata podataka, dobra praksa za buduće izmene
        event = EventGridEvent(
            event_type=event_type,
            data=data,
            subject="security-cam/detection",
            data_version="1.0"
        )

        # Šaljemo event na Topic — Event Grid preuzima odavde
        # i prosleđuje svim subscriberima koji slušaju ovaj event_type
        client.send([event])
        print(f"Event poslat: {event_type} — {data}")

    except Exception as ex:
        print('Exception:')
        print(ex)