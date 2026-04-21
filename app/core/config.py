from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")

    DATABASE_URL = (
        f"postgresql://{DB_USER}:{DB_PASSWORD}"
        f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )

    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
    JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS"))

    # Email verification settings
    VERIFICATION_CODE_EXPIRATION_MINUTES = int(os.getenv("VERIFICATION_CODE_EXPIRATION_MINUTES", "15"))
    VERIFICATION_CODE_MAX_ATTEMPTS = int(os.getenv("VERIFICATION_CODE_MAX_ATTEMPTS", "5"))

    # SMTP settings (used to send verification codes)
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    MAIL_FROM = os.getenv("MAIL_FROM", SMTP_USER)

    INVITATION_ACCEPT_URL_BASE = os.getenv(
        "INVITATION_ACCEPT_URL_BASE",
        "http://127.0.0.1:8000/auth/talleres/invitaciones/aceptar",
    )
    INVITATION_EXPIRATION_HOURS = int(os.getenv("INVITATION_EXPIRATION_HOURS", "48"))

settings = Settings()