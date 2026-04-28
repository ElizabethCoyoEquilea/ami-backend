from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import secrets
import string
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from jose import JWTError, jwt

from app.core.config import settings
from app.core.security import get_password_hash, generate_verification_code, hash_verification_code
from app.models.usuarios.cliente import Cliente
from app.models.usuarios.proveedor_servicio import ProveedorServicio
from app.models.usuarios.usuario import User
from app.models.usuarios.usuario_rol import UsuarioRol
from app.repositories.talleres_repository import (
    get_active_taller_by_id,
    list_active_provider_assignments_by_user,
)
from app.repositories.usuarios_repository import (
    create_user,
    get_active_user_role,
    get_cliente_by_codigo,
    get_cliente_by_user_id,
    get_user_by_email,
    get_role_by_id,
)
from app.schemas.usuarios.usuarios_schema import CurrentUserUpdate, UserCreate
from app.utils.email_sender import (
    send_verification_code_email,
    send_reset_password_email,
    send_taller_invitation_email,
    send_taller_invitation_accepted_email,
)


try:
    LA_PAZ_TZ = ZoneInfo("America/La_Paz")
except ZoneInfoNotFoundError:
    # Bolivia uses UTC-4 year-round. This fallback avoids requiring tzdata.
    LA_PAZ_TZ = timezone(timedelta(hours=-4))


PROVIDER_ROLE_ID = 2


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


def _generate_cliente_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "CLI" + "".join(secrets.choice(alphabet) for _ in range(length))


def create_client_for_current_user(db: Session, current_user: User):
    cliente_role_id = 3

    role = get_role_by_id(db, cliente_role_id)
    if not role or not role.activo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe el rol CLIENTE activo (id_rol=3)",
        )

    existing_cliente = get_cliente_by_user_id(db, current_user.id_usuario)
    if existing_cliente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya tiene un registro de cliente",
        )

    if get_active_user_role(db, current_user.id_usuario, cliente_role_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya tiene asignado el rol CLIENTE",
        )

    codigo_cliente = None
    for _ in range(10):
        candidate = _generate_cliente_code()
        if not get_cliente_by_codigo(db, candidate):
            codigo_cliente = candidate
            break

    if not codigo_cliente:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo generar un codigo de cliente unico",
        )

    usuario_rol = UsuarioRol(
        id_usuario=current_user.id_usuario,
        id_rol=cliente_role_id,
        activo=True,
    )
    cliente = Cliente(
        id_usuario=current_user.id_usuario,
        codigo=codigo_cliente,
    )

    db.add(usuario_rol)
    db.add(cliente)
    try:
        db.commit()
        db.refresh(cliente)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo crear el cliente",
        )

    return {
        "result": True,
        "message": "Rol CLIENTE asignado y cliente creado correctamente",
        "id_usuario": current_user.id_usuario,
        "id_rol": cliente_role_id,
        "id_cliente": cliente.id_cliente,
        "codigo_cliente": cliente.codigo,
    }


def check_current_user_is_client(db: Session, current_user: User):
    cliente = get_cliente_by_user_id(db, current_user.id_usuario)
    if not cliente:
        return {
            "is_client": False,
            "id_usuario": current_user.id_usuario,
            "id_cliente": None,
            "codigo_cliente": None,
        }

    return {
        "is_client": True,
        "id_usuario": current_user.id_usuario,
        "id_cliente": cliente.id_cliente,
        "codigo_cliente": cliente.codigo,
    }


def get_current_provider_profile(db: Session, current_user: User):
    provider_assignments = list_active_provider_assignments_by_user(
        db, current_user.id_usuario
    )
    if not provider_assignments:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario autenticado no tiene un rol activo de proveedor",
        )

    return {
        "usuario": {
            "id_usuario": current_user.id_usuario,
            "email": current_user.email,
            "activo": current_user.activo,
            "persona": {
                "id_persona": current_user.persona.id_persona,
                "nombre_completo": current_user.persona.nombre_completo,
                "fecha_nacimiento": current_user.persona.fecha_nacimiento,
                "genero": current_user.persona.genero,
                "telefono": current_user.persona.telefono,
                "documento": current_user.persona.documento,
            },
        },
        "empresas": [
            {
                "empresa": {
                    "id_taller": assignment.taller.id_taller,
                    "id_usuario": assignment.taller.id_usuario,
                    "nombre": assignment.taller.nombre,
                    "descripcion": assignment.taller.descripcion,
                    "radio_cobertura": assignment.taller.radio_cobertura,
                    "calificacion": assignment.taller.calificacion,
                    "direccion": assignment.taller.direccion,
                    "longitud": assignment.taller.longitud,
                    "latitud": assignment.taller.latitud,
                    "horario_inicio": assignment.taller.horario_inicio,
                    "horario_fin": assignment.taller.horario_fin,
                    "estado": assignment.taller.estado,
                    "activo": assignment.taller.activo,
                },
                "proveedor_servicio": {
                    "id_proveedor": assignment.id_proveedor,
                    "id_usuario": assignment.id_usuario,
                    "id_taller": assignment.id_taller,
                    "estado": assignment.estado,
                    "especialidad": assignment.especialidad,
                },
            }
            for assignment in provider_assignments
        ],
    }


def update_current_user_profile(
    db: Session,
    current_user: User,
    payload: CurrentUserUpdate,
) -> User:
    update_data = payload.model_dump(exclude_unset=True)

    nuevo_email = update_data.get("email")
    if nuevo_email and nuevo_email != current_user.email:
        existing_user = get_user_by_email(db, nuevo_email)
        if existing_user and existing_user.id_usuario != current_user.id_usuario:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El email ya esta registrado por otro usuario",
            )
        current_user.email = nuevo_email

    nueva_contrasena = update_data.get("contrasena")
    if nueva_contrasena:
        current_user.contrasena = get_password_hash(nueva_contrasena)

    persona_data = update_data.get("persona") or {}
    for field, value in persona_data.items():
        setattr(current_user.persona, field, value)

    try:
        db.commit()
        db.refresh(current_user)
        db.refresh(current_user.persona)
        return current_user
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo actualizar el usuario",
        )


def _create_taller_invitation_token(
    invited_user_id: int,
    email: str,
    id_taller: int,
    inviter_user_id: int,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.INVITATION_EXPIRATION_HOURS)
    payload = {
        "sub": str(invited_user_id),
        "email": email,
        "id_taller": id_taller,
        "id_usuario_invita": inviter_user_id,
        "scope": "taller_invitation",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _decode_taller_invitation_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de invitacion invalido o expirado",
        )

    if payload.get("scope") != "taller_invitation":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de invitacion invalido",
        )

    try:
        return {
            "id_usuario": int(payload.get("sub")),
            "email": str(payload.get("email")),
            "id_taller": int(payload.get("id_taller")),
            "id_usuario_invita": int(payload.get("id_usuario_invita")),
        }
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de invitacion invalido",
        )


def send_taller_invitation(db: Session, current_user: User, email: str, id_taller: int):
    invited_user = get_user_by_email(db, email)
    if not invited_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe un usuario con ese correo",
        )

    if not invited_user.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario invitado no esta activo",
        )

    provider_role = get_role_by_id(db, PROVIDER_ROLE_ID)
    if not provider_role or not provider_role.activo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe el rol PROVEEDOR DE SERVICIO activo (id_rol=2)",
        )

    taller = get_active_taller_by_id(db, id_taller)
    if not taller or taller.id_usuario != current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taller no encontrado para el usuario autenticado",
        )

    existing_assignment = (
        db.query(UsuarioRol)
        .filter(
            UsuarioRol.id_usuario == invited_user.id_usuario,
            UsuarioRol.id_rol == PROVIDER_ROLE_ID,
            UsuarioRol.id_taller == id_taller,
            UsuarioRol.activo == True,
        )
        .first()
    )
    if existing_assignment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya es proveedor de servicio en este taller",
        )

    invitation_token = _create_taller_invitation_token(
        invited_user_id=invited_user.id_usuario,
        email=invited_user.email,
        id_taller=taller.id_taller,
        inviter_user_id=current_user.id_usuario,
    )
    invitation_link = f"{settings.INVITATION_ACCEPT_URL_BASE}?token={invitation_token}"

    sent = send_taller_invitation_email(
        to_email=invited_user.email,
        invitation_link=invitation_link,
        taller_nombre=taller.nombre,
        taller_direccion=taller.direccion,
    )
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No se pudo enviar el correo de invitacion",
        )

    return {
        "result": True,
        "message": "Invitacion enviada correctamente",
        "invitation_link": invitation_link,
    }


def accept_taller_invitation(db: Session, token: str):
    invitation_data = _decode_taller_invitation_token(token)

    invited_user = get_user_by_email(db, invitation_data["email"])
    if not invited_user or invited_user.id_usuario != invitation_data["id_usuario"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario invitado no encontrado",
        )

    if not invited_user.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario invitado no esta activo",
        )

    provider_role = get_role_by_id(db, PROVIDER_ROLE_ID)
    if not provider_role or not provider_role.activo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe el rol PROVEEDOR DE SERVICIO activo (id_rol=2)",
        )

    taller = get_active_taller_by_id(db, invitation_data["id_taller"])
    if not taller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taller no encontrado",
        )

    if taller.id_usuario != invitation_data["id_usuario_invita"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La invitacion no coincide con el propietario del taller",
        )

    assignment = (
        db.query(UsuarioRol)
        .filter(
            UsuarioRol.id_usuario == invited_user.id_usuario,
            UsuarioRol.id_rol == PROVIDER_ROLE_ID,
            UsuarioRol.id_taller == taller.id_taller,
        )
        .first()
    )

    if assignment:
        assignment.activo = True
    else:
        assignment = UsuarioRol(
            id_usuario=invited_user.id_usuario,
            id_rol=PROVIDER_ROLE_ID,
            id_taller=taller.id_taller,
            activo=True,
        )
        db.add(assignment)

    proveedor_servicio = (
        db.query(ProveedorServicio)
        .filter(
            ProveedorServicio.id_usuario == invited_user.id_usuario,
            ProveedorServicio.id_taller == taller.id_taller,
        )
        .first()
    )

    if not proveedor_servicio:
        proveedor_servicio = ProveedorServicio(
            id_usuario=invited_user.id_usuario,
            id_taller=taller.id_taller,
            estado="Disponible",
            especialidad=None,
        )
        db.add(proveedor_servicio)

    try:
        db.commit()
        db.refresh(assignment)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo aceptar la invitacion",
        )

    sent = send_taller_invitation_accepted_email(
        to_email=invited_user.email,
        taller_nombre=taller.nombre,
        taller_direccion=taller.direccion,
    )
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Invitacion aceptada, pero no se pudo enviar el correo de confirmacion",
        )

    return {
        "result": True,
        "message": "Invitacion aceptada correctamente. Ahora eres proveedor de servicio de este taller",
        "id_usuario": invited_user.id_usuario,
        "id_taller": taller.id_taller,
        "id_rol": PROVIDER_ROLE_ID,
    }
