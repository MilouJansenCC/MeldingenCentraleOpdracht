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
    logger.error("🚨 WEBHOOK ONTVANGEN")
    data = await request.json()

    edits = data.get("edits", {})
    features = edits.get("adds", []) + edits.get("updates", [])

    for feature in features:
        attrs = feature.get("attributes", {})
        bijzonderheden = attrs.get("Bijzonderheden")

        if bijzonderheden in ["Eikenprocessierups", "Iepziekte"]:
            logger.error(f"📧 Mail trigger: {bijzonderheden}")
            send_email(bijzonderheden, attrs)

    return {"status": "ok"}

def send_email(bijzonderheden, attrs):
    regels = [f"Nieuwe melding: {bijzonderheden}\n"]
    for veld in VELDEN:
        regels.append(f"{veld}: {attrs.get(veld, 'n.v.t.')}")
    body = "\n".join(regels)

    msg = MIMEText(body)
    msg["Subject"] = f"Nieuwe melding: {bijzonderheden}"
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(FROM_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
            logger.error("✅ Mail verzonden")
    except Exception as e:
        logger.error(f"❌ Mail fout: {e}")
