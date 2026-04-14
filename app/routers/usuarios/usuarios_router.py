from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.usuarios.usuarios_schema import (
    UserCreate,
    AdminCreate,
    UserResponse,
    VerifyUserSchema,
    ResendVerificationSchema,
    MessageResponse,
    RegistrationResponse,
)
from app.services.usuarios_service import (
    register_user,
    register_admin,
    register_client,
    verify_user_email,
    resend_verification_code,
)


router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post("/", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    register_user(db, user_data)
    return {"registered": True}


@router.post("/register/admin", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
def create_admin(admin_data: AdminCreate, db: Session = Depends(get_db)):
    """
    Registra un nuevo administrador (usuario con rol id=1).
    El rol se asigna automaticamente.
    """
    register_admin(db, admin_data)
    return {"registered": True}


@router.post("/register/client", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
def create_client(client_data: UserCreate, db: Session = Depends(get_db)):
    """
    Registra un nuevo cliente (usuario con rol id=3).
    El rol se asigna automaticamente y requiere verificacion de correo.
    """
    register_client(db, client_data)
    return {"registered": True}


@router.post("/verify", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def verify_user(payload: VerifyUserSchema, db: Session = Depends(get_db)):
    return verify_user_email(db, payload.email, payload.codigo)


@router.post("/verify/resend", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def resend_code(payload: ResendVerificationSchema, db: Session = Depends(get_db)):
    return resend_verification_code(db, payload.email)
