import os
import json
import logging
import smtplib
from urllib.parse import parse_qs
from email.mime.text import MIMEText

import requests
from fastapi import FastAPI, Request

# -------------------------------------------------
# App & logging
# -------------------------------------------------
app = FastAPI()
logger = logging.getLogger("uvicorn.error")

# -------------------------------------------------
# Velden die je in de mail wilt
# -------------------------------------------------
VELDEN = [
    "Id", "Stadsdeel", "Buurt", "Wijk", "Beheergebieden",
    "Boom_nummer", "Boomsoort_Nederlands", "Boomsoort_Wetenschappelijk",
    "Stamdiameterklasse", "Beheertype", "Boom_leeftijdsklasse",
    "Leeftijd", "Snoei_vorm", "Vormsnoei_jaar", "Boombeeld"
]

# -------------------------------------------------
# Mail instellingen (Railway variables)
# -------------------------------------------------
FROM_EMAIL = os.getenv("FROM_EMAIL")
TO_EMAIL = os.getenv("TO_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.office365.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

# -------------------------------------------------
# Webhook endpoint
# -------------------------------------------------
@app.post("/arcgis-webhook")
async def arcgis_webhook(request: Request):
    logger.error("🚨 WEBHOOK ONTVANGEN")

    body = await request.body()
    if not body:
        logger.error("ℹ️ Lege body (ArcGIS handshake)")
        return {"status": "empty"}

    parsed = parse_qs(body.decode())
    if "payload" not in parsed:
        logger.error("❌ Geen payload gevonden")
        return {"status": "no payload"}

    payload = json.loads(parsed["payload"][0])
    logger.error(f"📦 Payload ontvangen ({len(payload)} items)")

    for item in payload:
        changes_url = item.get("changesUrl")
        if not changes_url:
            continue

        changes_url = requests.utils.unquote(changes_url)
        logger.error(f"🔗 Changes URL: {changes_url}")

        try:
            process_changes(changes_url)
        except Exception as e:
            logger.error(f"❌ Fout bij verwerken changes: {e}", exc_info=True)

    return {"status": "ok"}

# -------------------------------------------------
# Haal wijzigingen op uit ArcGIS
# -------------------------------------------------
def process_changes(changes_url: str):
    response = requests.get(changes_url, timeout=30)
    response.raise_for_status()

    data = response.json()
    logger.error("📥 Changes opgehaald")

    updates = data.get("updates", [])

    if not updates:
        logger.error("ℹ️ Geen updates in changes")
        return

    for feature in updates:
        attrs = feature.get("attributes", {})
        bijzonderheden = attrs.get("Bijzonderheden")

        if bijzonderheden in ["Iepziekte", "Eikenprocessierups"]:
            logger.error(f"📧 Relevante melding: {bijzonderheden}")
            send_email(bijzonderheden, attrs)
        else:
            logger.error(f"ℹ️ Geen relevante bijzonderheid: {bijzonderheden}")

# -------------------------------------------------
# Mail versturen
# -------------------------------------------------
def send_email(bijzonderheden: str, attrs: dict):
    regels = [f"Nieuwe melding: {bijzonderheden}", ""]

    for veld in VELDEN:
        regels.append(f"{veld}: {attrs.get(veld, 'n.v.t.')}")

    body = "\n".join(regels)

    msg = MIMEText(body)
    msg["Subject"] = f"Nieuwe melding: {bijzonderheden}"
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(FROM_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)

    logger.error("✅ Mail verzonden")
