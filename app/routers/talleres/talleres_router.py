from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuarios.usuario import User
from app.schemas.talleres.taller_schema import TallerCreate, TallerResponse, TallerUpdate
from app.schemas.usuarios.usuarios_schema import MessageResponse
from app.services.talleres_service import (
    eliminar_taller,
    listar_talleres_por_usuario,
    listar_talleres,
    modificar_taller,
    obtener_taller,
    registrar_taller,
)


router = APIRouter(prefix="/talleres", tags=["Talleres"])


@router.post("", response_model=TallerResponse, status_code=status.HTTP_201_CREATED)
def crear_taller(
    taller_data: TallerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return registrar_taller(db, taller_data, current_user.id_usuario)


@router.get("", response_model=list[TallerResponse], status_code=status.HTTP_200_OK)
def obtener_talleres(db: Session = Depends(get_db)):
    return listar_talleres(db)


@router.get("/mis-talleres", response_model=list[TallerResponse], status_code=status.HTTP_200_OK)
def obtener_mis_talleres(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return listar_talleres_por_usuario(db, current_user.id_usuario)


@router.get("/{id_taller}", response_model=TallerResponse, status_code=status.HTTP_200_OK)
def obtener_taller_por_id(id_taller: int, db: Session = Depends(get_db)):
    return obtener_taller(db, id_taller)


@router.put("/{id_taller}", response_model=TallerResponse, status_code=status.HTTP_200_OK)
def actualizar_taller(
    id_taller: int,
    taller_data: TallerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return modificar_taller(db, id_taller, taller_data, current_user.id_usuario)


@router.delete("/{id_taller}", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def borrar_taller(id_taller: int, db: Session = Depends(get_db)):
    return eliminar_taller(db, id_taller)
