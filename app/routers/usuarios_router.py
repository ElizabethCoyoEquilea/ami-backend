from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.usuarios.usuarios_schema import UserCreate, AdminCreate, UserResponse
from app.services.usuarios_service import register_user, register_admin


router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    return register_user(db, user_data)


@router.post("/register/admin", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_admin(admin_data: AdminCreate, db: Session = Depends(get_db)):
    """
    Registra un nuevo administrador (usuario con rol id=1).
    El rol se asigna automaticamente.
    """
    return register_admin(db, admin_data)
