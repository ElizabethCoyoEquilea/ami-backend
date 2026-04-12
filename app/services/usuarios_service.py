from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.repositories.usuarios_repository import (
    create_user,
    get_user_by_email,
    create_user_with_role,
    get_role_by_id,
)
from app.schemas.usuarios.usuarios_schema import UserCreate, AdminCreate


def register_user(db: Session, user_data: UserCreate):
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya esta registrado",
        )

    hashed_password = get_password_hash(user_data.contrasena)
    return create_user(db, user_data, hashed_password)


def register_admin(db: Session, admin_data: AdminCreate):
    """Registra un usuario como administrador (rol_id=1)."""
    existing_user = get_user_by_email(db, admin_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya esta registrado",
        )

    hashed_password = get_password_hash(admin_data.contrasena)
    # rol_id=1 es para administrador
    admin_role = get_role_by_id(db, 1)
    if not admin_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No existe el rol administrador con id_rol=1",
        )

    try:
        return create_user_with_role(db, admin_data, hashed_password, rol_id=1)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo registrar el admin por un conflicto de datos",
        )
