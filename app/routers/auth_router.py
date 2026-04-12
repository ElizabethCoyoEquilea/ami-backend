from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_current_user
from app.schemas.usuarios.usuarios_schema import LoginSchema, TokenResponse
from app.repositories.usuarios_repository import get_user_by_email
from app.models.usuarios.usuario import User

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
        "token_type": "bearer",
        "usuario": usuario
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
