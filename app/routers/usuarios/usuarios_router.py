from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.usuarios.usuarios_schema import (
    UserCreate,
    VerifyUserSchema,
    ResendVerificationSchema,
    MessageResponse,
    RegistrationResponse,
)
from app.services.usuarios_service import (
    register_user,
    verify_user_email,
    resend_verification_code,
)


router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post("/register", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    register_user(db, user_data)
    return {"registered": True}


@router.post("/verify", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def verify_user(payload: VerifyUserSchema, db: Session = Depends(get_db)):
    return verify_user_email(db, payload.email, payload.codigo)


@router.post("/verify/resend", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def resend_code(payload: ResendVerificationSchema, db: Session = Depends(get_db)):
    return resend_verification_code(db, payload.email)
