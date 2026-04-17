from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuarios.usuario import User
from app.schemas.usuarios.usuarios_schema import MessageResponse
from app.schemas.usuarios.vehiculo_schema import (
    VehiculoCreate,
    VehiculoResponse,
    VehiculoUpdate,
)
from app.services.vehiculos_service import (
    eliminar_vehiculo,
    listar_mis_vehiculos,
    modificar_vehiculo,
    registrar_vehiculo,
)


router = APIRouter(prefix="/vehiculos", tags=["Vehiculos"])


@router.post("", response_model=VehiculoResponse, status_code=status.HTTP_201_CREATED)
def crear_vehiculo(
    vehiculo_data: VehiculoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return registrar_vehiculo(db, vehiculo_data, current_user)


@router.get("/mis-vehiculos", response_model=list[VehiculoResponse], status_code=status.HTTP_200_OK)
def obtener_mis_vehiculos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return listar_mis_vehiculos(db, current_user)


@router.put("/{id_vehiculo}", response_model=VehiculoResponse, status_code=status.HTTP_200_OK)
def actualizar_vehiculo(
    id_vehiculo: int,
    vehiculo_data: VehiculoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return modificar_vehiculo(db, id_vehiculo, vehiculo_data, current_user)


@router.delete("/{id_vehiculo}", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def borrar_vehiculo(
    id_vehiculo: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return eliminar_vehiculo(db, id_vehiculo, current_user)
