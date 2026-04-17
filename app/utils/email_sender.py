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


def send_taller_invitation_email(
    to_email: str,
    invitation_link: str,
    taller_nombre: str,
    taller_direccion: str,
) -> bool:
    """Envia un correo de invitacion para unirse como proveedor a un taller."""
    if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        return False

    recipient = to_email.strip()
    sender = settings.MAIL_FROM or settings.SMTP_USER

    message = EmailMessage()
    message["Subject"] = "Invitacion a taller"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        (
            "Recibiste una invitacion para unirte como proveedor de servicio al taller:\n"
            f"- Nombre: {taller_nombre}\n"
            f"- Direccion: {taller_direccion}\n\n"
            "Haz clic en el siguiente enlace para aceptar la invitacion:\n"
            f"{invitation_link}\n\n"
            f"Este enlace vence en {settings.INVITATION_EXPIRATION_HOURS} horas."
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


def send_taller_invitation_accepted_email(
    to_email: str,
    taller_nombre: str,
    taller_direccion: str,
) -> bool:
    """Envia confirmacion cuando una invitacion a taller fue aceptada."""
    if not settings.SMTP_HOST or not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        return False

    recipient = to_email.strip()
    sender = settings.MAIL_FROM or settings.SMTP_USER

    message = EmailMessage()
    message["Subject"] = "Invitacion aceptada"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        (
            "Aceptaste correctamente la invitacion y ahora eres proveedor de servicio del taller:\n"
            f"- Nombre: {taller_nombre}\n"
            f"- Direccion: {taller_direccion}\n\n"
            "Ya puedes operar como proveedor de servicio en este taller."
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
