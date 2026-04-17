from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_current_user
from app.schemas.usuarios.usuarios_schema import (
    LoginSchema,
    TokenResponse,
    ResetPasswordSchema,
    ResultMessageResponse,
    CreateClientResponse,
    ClientAssignmentResponse,
    TallerInvitationCreateSchema,
    TallerInvitationCreateResponse,
    TallerInvitationAcceptResponse,
)
from app.repositories.usuarios_repository import get_user_by_email
from app.models.usuarios.usuario import User
from app.services.usuarios_service import (
    reset_user_password,
    create_client_for_current_user,
    check_current_user_is_client,
    send_taller_invitation,
    accept_taller_invitation,
)

router = APIRouter(prefix="/auth", tags=["Autenticacion"])


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(credentials: LoginSchema, db: Session = Depends(get_db)):
    """
    Endpoint de login que valida email y contrasena, devuelve un token JWT.
    """
    usuario = get_user_by_email(db, credentials.email)
    
    if not usuario or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contrasena incorrecta",
        )
    
    if not verify_password(credentials.contrasena, usuario.contrasena):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contrasena incorrecta",
        )
    
    access_token = create_access_token(usuario.id_usuario, usuario.email)
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=dict, status_code=status.HTTP_200_OK)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Endpoint protegido que devuelve los datos del usuario actual (desde el token JWT).
    
    Requiere: Authorization: Bearer <token>
    """
    return {
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
        }
    }


@router.post("/reset-password", response_model=ResultMessageResponse, status_code=status.HTTP_200_OK)
def reset_password(payload: ResetPasswordSchema, db: Session = Depends(get_db)):
    return reset_user_password(db, payload.email)


@router.post("/create-client", response_model=CreateClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Asigna el rol CLIENTE (id_rol=3) al usuario autenticado y crea su registro en cliente.

    Requiere: Authorization: Bearer <token>
    """
    return create_client_for_current_user(db, current_user)


@router.get("/is-client", response_model=ClientAssignmentResponse, status_code=status.HTTP_200_OK)
def is_client(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Verifica si el usuario autenticado tiene un registro en la tabla cliente.

    Requiere: Authorization: Bearer <token>
    """
    return check_current_user_is_client(db, current_user)


@router.post(
    "/talleres/invitaciones",
    response_model=TallerInvitationCreateResponse,
    status_code=status.HTTP_200_OK,
)
def create_taller_invitation(
    payload: TallerInvitationCreateSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Envia una invitacion por correo para que un usuario sea proveedor de un taller."""
    return send_taller_invitation(db, current_user, payload.email, payload.id_taller)


@router.get(
    "/talleres/invitaciones/aceptar",
    response_model=TallerInvitationAcceptResponse,
    status_code=status.HTTP_200_OK,
)
def accept_invitation(token: str, db: Session = Depends(get_db)):
    """Acepta una invitacion de taller usando el token recibido por correo."""
    return accept_taller_invitation(db, token)
