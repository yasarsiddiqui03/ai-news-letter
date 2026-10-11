import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Config:
    PORT = int(os.getenv("PORT", 5000))
    DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    DEV_MODE = os.getenv("DEV_MODE", "True").lower() in ("true", "1", "yes")

    SECRET_KEY = os.getenv("SECRET_KEY", "ai-news-letter-super-secret-key-2026-production")
    JWT_SECRET = os.getenv("JWT_SECRET", "ai-news-letter-jwt-secret-key-production-grade-2026")
    JWT_EXPIRY_DAYS = 7

    DATABASE_PATH = BASE_DIR / "backend" / "ai_news.db"

    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
    GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID", "").strip()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "").strip()
    FAST2SMS_API_KEY = os.getenv("FAST2SMS_API_KEY", "").strip()

    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USER = os.getenv("SMTP_USER", "").strip()
    SMTP_PASS = os.getenv("SMTP_PASS", "").strip()
    SMTP_FROM = os.getenv("SMTP_FROM", "no-reply@ainewsletter.com").strip()

    ADMIN_ID = os.getenv("ADMIN_ID", "admin").strip()
    ADMIN_PASSWORD_HASH = os.getenv(
        "ADMIN_PASSWORD_HASH",
        "$2b$12$yzFLszQMSBsHY8uUhuIYOeVWk3epZ5VBCE659yGxEZWEz2YEjf5qi"
    ).strip()
    ADMIN_TOTP_SECRET = os.getenv(
        "ADMIN_TOTP_SECRET",
        "VMVN5V3QCWYR43SSYUXGLIZUV2IMPUVG"
    ).strip()
