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


def analyze_image_with_cv(image_data: bytes):
    """Šalje bajtove slike Azure Computer Vision servisu na analizu."""
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
        # Poziv Computer Vision servisa (koristimo analyze umesto analyze_from_url za bajtove)
        result = client.analyze(
            image_data=image_data,
            visual_features=[
                VisualFeatures.TAGS,
                VisualFeatures.OBJECTS,
            ],
        )

        logging.info("--- 👁️ REZULTATI ANALIZE SLIKE ---")

        # 1. Tagovi (Oznake)
        if result.tags is not None:
            tags = [tag.name for tag in result.tags.list]
            logging.info(f"🏷️  Tagovi: {', '.join(tags)}")

        # 2. Detektovani objekti
        if result.objects is not None:
            for obj in result.objects.list:
                if not obj.tags:
                    continue
                logging.info(
                    f"📦 Detektovan objekat: {obj.tags[0].name} (Pouzdanost: {obj.tags[0].confidence:.2f})"
                )

    except Exception as e:
        logging.error(f"❌ Greška prilikom Computer Vision analize: {str(e)}")


@app.function_name("analyze-image")
@app.blob_trigger(arg_name="myblob", path="face-snapshots/{name}", connection="AzureWebJobsStorage")
def analyze_image(myblob: func.InputStream):
    logging.info(f"✅ Azure Function (Blob Trigger) se aktivirala za blob: {myblob.name}")

    try:
        # Čitamo sadržaj bloba u bajtove
        image_data = myblob.read()
        
        if image_data:
            # POZIV COMPUTER VISION ANALIZE
            analyze_image_with_cv(image_data)
        else:
            logging.warning("⚠️ Blob je prazan, preskačem analizu.")

    except Exception as e:
        logging.error(f"❌ Greška: {str(e)}")
