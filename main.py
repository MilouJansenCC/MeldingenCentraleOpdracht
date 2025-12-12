import os
import logging
import smtplib
from email.mime.text import MIMEText
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()
logger = logging.getLogger("uvicorn.error")

VELDEN = [
    "Id", "Stadsdeel", "Buurt", "Wijk", "Beheergebieden",
    "Boom_nummer", "Boomsoort_Nederlands", "Boomsoort_Wetenschappelijk",
    "Stamdiameterklasse", "Beheertype", "Boom_leeftijdsklasse",
    "Leeftijd", "Snoei_vorm", "Vormsnoei_jaar", "Boombeeld"
]

# Read configuration from environment variables (set these in Railway)
FROM_EMAIL = os.getenv("FROM_EMAIL")
TO_EMAIL = os.getenv("TO_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.office365.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

if not FROM_EMAIL or not TO_EMAIL or not SMTP_PASSWORD:
    logger.warning("FROM_EMAIL, TO_EMAIL or SMTP_PASSWORD not set. Email sending will fail until configured.")

@app.post("/arcgis-webhook")
async def arcgis_webhook(request: Request):
    try:
        data = await request.json()
    except Exception as e:
        logger.exception("Invalid JSON in request")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    edits = data.get("edits", {}) or {}
    adds = edits.get("adds", []) or []
    updates = edits.get("updates", []) or []
    features = list(adds) + list(updates)

    for feature in features:
        attrs = feature.get("attributes", {}) or {}
        bijzonderheden = attrs.get("Bijzonderheden")
        if bijzonderheden in ["Eikenprocessierups", "Iepziekte"]:
            try:
                send_email(bijzonderheden, attrs)
            except Exception:
                logger.exception("Failed to send email for feature: %s", attrs.get("Id"))

    return {"status": "ok"}


def send_email(bijzonderheden: str, attrs: dict):
    if not (FROM_EMAIL and TO_EMAIL and SMTP_PASSWORD):
        logger.error("Email env vars not configured (FROM_EMAIL/TO_EMAIL/SMTP_PASSWORD). Aborting send.")
        return

    body_lines = [f"Nieuwe melding van {bijzonderheden}:\n"]
    for veld in VELDEN:
        waarde = attrs.get(veld, "n.v.t.")
        body_lines.append(f"{veld}: {waarde}")
    body = "\n".join(body_lines)

    msg = MIMEText(body)
    msg["Subject"] = f"Nieuwe melding: {bijzonderheden}"
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL

    logger.info("Connecting to SMTP %s:%s", SMTP_HOST, SMTP_PORT)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.starttls()
        server.login(FROM_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
    logger.info("Email sent for melding %s (Id=%s)", bijzonderheden, attrs.get("Id"))
