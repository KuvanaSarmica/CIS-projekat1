import azure.functions as func
import json
import logging
import os

from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential

app = func.FunctionApp()

# Podešavanje Computer Vision klijenta preko enviroment promenljivih
# Napomena: Ove vrednosti podesi u local.settings.json ili App Settings na Azure portal-u
VISION_ENDPOINT = os.getenv("AZURE_VISION_ENDPOINT")
VISION_KEY = os.getenv("AZURE_VISION_KEY")


def analyze_image_with_cv(image_url: str):
    """S šalje URL slike Azure Computer Vision servisu na analizu."""
    if not VISION_ENDPOINT or not VISION_KEY:
        logging.error(
            "❌ Fale VISION_ENDPOINT ili VISION_KEY u konfiguraciji!"
        )
        return

    # Inicijalizacija klijenta
    client = ImageAnalysisClient(
        endpoint=VISION_ENDPOINT, credential=AzureKeyCredential(VISION_KEY)
    )

    try:
        # Poziv Computer Vision servisa
        result = client.analyze_from_url(
            image_url=image_url,
            visual_features=[
                VisualFeatures.CAPTION,
                VisualFeatures.TAGS,
                VisualFeatures.OBJECTS,
            ],
        )

        logging.info("--- 👁️ REZULTATI ANALIZE SLIKE ---")

        # 1. Opis slike (Caption)
        if result.caption is not None:
            logging.info(
                f"📝 Opis: '{result.caption.text}' (Pouzdanost: {result.caption.confidence:.2f})"
            )

        # 2. Tagovi (Oznake)
        if result.tags is not None:
            tags = [tag.name for tag in result.tags.values]
            logging.info(f"🏷️  Tagovi: {', '.join(tags)}")

        # 3. Detektovani objekti
        if result.objects is not None:
            for obj in result.objects.values:
                logging.info(
                    f"📦 Detektovan objekat: {obj.tags[0].name} (Pouzdanost: {obj.tags[0].confidence:.2f})"
                )

    except Exception as e:
        logging.error(f"❌ Greška prilikom Computer Vision analize: {str(e)}")


@app.function_name("analyze-image")
@app.route(route="analyze-image", methods=["POST"])
def analyze_image(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("✅ Azure Function se pokrenut!")

    try:
        events = req.get_json()

        for i, event in enumerate(events):
            event_type = event.get("eventType")

            if event_type == "Microsoft.Storage.BlobCreated":
                blob_url = event["data"]["url"]
                blob_name = blob_url.split("/")[-1]

                logging.info(f"🖼️  Slika uploadovana: {blob_name}")
                logging.info(f"🔗 URL: {blob_url}")

                # POZIV COMPUTER VISION ANALIZE
                analyze_image_with_cv(blob_url)

        return func.HttpResponse("OK", status_code=200)

    except Exception as e:
        logging.error(f"❌ Greška: {str(e)}")
        return func.HttpResponse("Greška", status_code=400)