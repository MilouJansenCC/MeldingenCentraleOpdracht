import os
import logging
import smtplib
from email.mime.text import MIMEText
from fastapi import FastAPI, Request

app = FastAPI()
logger = logging.getLogger("uvicorn.error")

VELDEN = [
    "Id", "Stadsdeel", "Buurt", "Wijk", "Beheergebieden",
    "Boom_nummer", "Boomsoort_Nederlands", "Boomsoort_Wetenschappelijk",
    "Stamdiameterklasse", "Beheertype", "Boom_leeftijdsklasse",
    "Leeftijd", "Snoei_vorm", "Vormsnoei_jaar", "Boombeeld"
]

FROM_EMAIL = os.getenv("FROM_EMAIL")
TO_EMAIL = os.getenv("TO_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.office365.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))


@app.post("/arcgis-webhook")
async def webhook(request: Request):
    try:
        logger.error("🚨 WEBHOOK ONTVANGEN")
        data = await request.json()
        logger.error(f"Payload: {data}")

        edits = data.get("edits")
        if not edits:
            logger.error("⚠️ Geen 'edits' in payload")
            return {"status": "no edits"}

        features = []
        features.extend(edits.get("adds", []))
        features.extend(edits.get("updates", []))

        if not features:
            logger.error("⚠️ Geen adds of updates gevonden")
            return {"status": "no features"}

        for feature in features:
            attrs = feature.get("attributes", {})
            bijzonderheden = attrs.get("Bijzonderheden")

            if bijzonderheden in ["Eikenprocessierups", "Iepziekte"]:
                logger.error(f"📧 Mail trigger: {bijzonderheden}")
                send_email(bijzonderheden, attrs)
            else:
                logger.error(f"ℹ️ Geen relevante bijzonderheid: {bijzonderheden}")

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"❌ Fout in webhook: {e}", exc_info=True)
        return {"status": "error"}
