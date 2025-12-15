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

@app.post("https://meldingencentraleopdracht-production.up.railway.app/arcgis-webhook
")
async def webhook(request: Request):
    print("🚨 WEBHOOK ONTVANGEN")
    data = await request.json()
    print(data)
    
