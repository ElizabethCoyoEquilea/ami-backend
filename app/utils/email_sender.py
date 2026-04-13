import smtplib
from email.message import EmailMessage

from app.core.config import settings


def send_verification_code_email(to_email: str, code: str) -> bool:
    """Envia el codigo de verificacion por SMTP. Devuelve True si fue enviado."""
    if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        return False

    recipient = to_email.strip()
    sender = settings.MAIL_FROM or settings.SMTP_USER

    message = EmailMessage()
    message["Subject"] = "Codigo de verificacion"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        (
            "Tu codigo de verificacion es: "
            f"{code}\n\n"
            f"Este codigo vence en {settings.VERIFICATION_CODE_EXPIRATION_MINUTES} minutos."
        )
    )

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)
        return True
    except Exception:
        return False


def send_reset_password_email(to_email: str, new_password: str) -> bool:
    """Envia una nueva contrasena temporal por SMTP. Devuelve True si fue enviado."""
    if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        return False

    recipient = to_email.strip()
    sender = settings.MAIL_FROM or settings.SMTP_USER

    message = EmailMessage()
    message["Subject"] = "Restablecimiento de contrasena"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        (
            "Se solicito el restablecimiento de tu contrasena. "
            f"Tu nueva contrasena temporal es: {new_password}\n\n"
            "Te recomendamos cambiarla despues de iniciar sesion."
        )
    )

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)
        return True
    except Exception:
        return False
