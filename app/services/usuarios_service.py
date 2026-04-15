from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import secrets
import string
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import settings
from app.core.security import get_password_hash, generate_verification_code, hash_verification_code
from app.repositories.usuarios_repository import (
    create_user,
    get_user_by_email,
)
from app.schemas.usuarios.usuarios_schema import UserCreate
from app.utils.email_sender import send_verification_code_email, send_reset_password_email


try:
    LA_PAZ_TZ = ZoneInfo("America/La_Paz")
except ZoneInfoNotFoundError:
    # Bolivia uses UTC-4 year-round. This fallback avoids requiring tzdata.
    LA_PAZ_TZ = timezone(timedelta(hours=-4))


def _generate_random_password(length: int = 8) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def register_user(db: Session, user_data: UserCreate):
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya esta registrado",
        )

    hashed_password = get_password_hash(user_data.contrasena)
    verification_code = generate_verification_code()
    verification_code_hash = hash_verification_code(verification_code)
    verification_expiration = datetime.now(LA_PAZ_TZ) + timedelta(
        minutes=settings.VERIFICATION_CODE_EXPIRATION_MINUTES
    )

    user = create_user(
        db,
        user_data,
        hashed_password,
        activo=False,
        codigo_verificacion_hash=verification_code_hash,
        codigo_verificacion_expira_en=verification_expiration,
        codigo_verificacion_intentos=0,
    )

    sent = send_verification_code_email(user.email, verification_code)
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Usuario creado, pero no se pudo enviar el correo de verificacion",
        )
    return user


def verify_user_email(db: Session, email: str, code: str):
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    if user.activo:
        return {"message": "El usuario ya se encuentra verificado"}

    if not user.codigo_verificacion_hash or not user.codigo_verificacion_expira_en:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No existe un codigo de verificacion activo",
        )

    now = datetime.now(LA_PAZ_TZ)
    expiration = user.codigo_verificacion_expira_en
    if expiration.tzinfo is None:
        expiration = expiration.replace(tzinfo=LA_PAZ_TZ)
    else:
        expiration = expiration.astimezone(LA_PAZ_TZ)

    if now > expiration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El codigo de verificacion expiro",
        )

    if user.codigo_verificacion_intentos >= settings.VERIFICATION_CODE_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Se supero la cantidad maxima de intentos. Solicita un nuevo codigo",
        )

    incoming_hash = hash_verification_code(code)
    if not secrets.compare_digest(user.codigo_verificacion_hash, incoming_hash):
        user.codigo_verificacion_intentos += 1
        db.commit()
        remaining_attempts = max(
            settings.VERIFICATION_CODE_MAX_ATTEMPTS - user.codigo_verificacion_intentos,
            0,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Codigo incorrecto. Intentos restantes: {remaining_attempts}",
        )

    user.activo = True
    user.codigo_verificacion_hash = None
    user.codigo_verificacion_expira_en = None
    user.codigo_verificacion_intentos = 0
    db.commit()
    return {"message": "Usuario verificado correctamente"}


def resend_verification_code(db: Session, email: str):
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    if user.activo:
        return {"message": "El usuario ya se encuentra verificado"}

    verification_code = generate_verification_code()
    verification_code_hash = hash_verification_code(verification_code)
    verification_expiration = datetime.now(LA_PAZ_TZ) + timedelta(
        minutes=settings.VERIFICATION_CODE_EXPIRATION_MINUTES
    )

    # Invalidar codigo anterior y reiniciar intentos.
    user.codigo_verificacion_hash = verification_code_hash
    user.codigo_verificacion_expira_en = verification_expiration
    user.codigo_verificacion_intentos = 0
    db.commit()

    sent = send_verification_code_email(user.email, verification_code)
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo enviar el nuevo codigo de verificacion",
        )
    return {"message": "Se envio un nuevo codigo de verificacion"}


def reset_user_password(db: Session, email: str):
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario no esta activo",
        )

    new_password = _generate_random_password(8)
    sent = send_reset_password_email(user.email, new_password)
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo enviar el correo de restablecimiento",
        )

    user.contrasena = get_password_hash(new_password)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo actualizar la contrasena",
        )

    return {"result": True, "message": "Se envio una nueva contrasena al correo registrado"}
