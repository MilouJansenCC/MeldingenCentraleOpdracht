import os
import logging
import smtplib
from email.mime.text import MIMEText
from fastapi import FastAPI, Request, HTTPException
import requests
import json

app = FastAPI()
logger = logging.getLogger("uvicorn.error")

VELDEN = [
    "Id", "Stadsdeel", "Buurt", "Wijk", "Beheergebieden",
    "Boom_nummer", "Boomsoort_Nederlands", "Boomsoort_Wetenschappelijk",
    "Stamdiameterklasse", "Beheertype", "Boom_leeftijdsklasse",
    "Leeftijd", "Snoei_vorm", "Vormsnoei_jaar", "Boombeeld"
]

# Environment config
FROM_EMAIL = os.getenv("FROM_EMAIL")
TO_EMAIL = os.getenv("TO_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.office365.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

# SendGrid/API config
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")

if not FROM_EMAIL or not TO_EMAIL:
    logger.warning("FROM_EMAIL or TO_EMAIL not set. Email sending will fail until configured.")

@app.post("/arcgis-webhook")
async def arcgis_webhook(request: Request):
    try:
        data = await request.json()
    except Exception:
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
    """Send email using SendGrid API if available, otherwise attempt SMTP fallback."""
    subject = f"Nieuwe melding: {bijzonderheden}"

    body_lines = [f"Nieuwe melding van {bijzonderheden}:\n"]
    for veld in VELDEN:
        waarde = attrs.get(veld, "n.v.t.")
        body_lines.append(f"{veld}: {waarde}")
    body = "\n".join(body_lines)

    # If SendGrid API key is set, use the HTTP API (recommended for Railway)
    if SENDGRID_API_KEY:
        logger.info("Sending email via SendGrid API")
        url = "https://api.sendgrid.com/v3/mail/send"
        payload = {
            "personalizations": [
                {"to": [{"email": TO_EMAIL}], "subject": subject}
            ],
            "from": {"email": FROM_EMAIL},
            "content": [{"type": "text/plain", "value": body}]
        }
        headers = {
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json"
        }
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)
        if resp.status_code not in (200, 202):
            logger.error("SendGrid failed: %s %s", resp.status_code, resp.text)
            raise RuntimeError(f"SendGrid error: {resp.status_code}")
        logger.info("Email sent via SendGrid for melding %s (Id=%s)", bijzonderheden, attrs.get("Id"))
        return

    # Fallback: attempt SMTP (may fail if Railway blocks outbound SMTP)
    if not (FROM_EMAIL and TO_EMAIL and SMTP_PASSWORD):
        logger.error("Email env vars not configured (FROM_EMAIL/TO_EMAIL/SMTP_PASSWORD). Aborting send.")
        return

    logger.info("Connecting to SMTP %s:%s", SMTP_HOST, SMTP_PORT)
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = FROM_EMAIL
        msg["To"] = TO_EMAIL

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
            server.starttls()
            server.login(FROM_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("Email sent via SMTP for melding %s (Id=%s)", bijzonderheden, attrs.get("Id"))
    except Exception:
        logger.exception("SMTP send failed")
        raise
