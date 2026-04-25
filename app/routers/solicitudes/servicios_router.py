from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuarios.usuario import User
from app.schemas.solicitudes.servicio_schema import (
    DetalleServicioCreate,
    DetalleServicioResponse,
    ServicioCreate,
    ServicioResponse,
)
from app.services.servicios_service import (
    listar_detalles_servicio,
    listar_servicios_asignacion,
    obtener_servicio,
    registrar_detalle_servicio,
    registrar_servicio,
)


router = APIRouter(prefix="/servicios", tags=["Servicios"])


@router.post("", response_model=ServicioResponse, status_code=status.HTTP_201_CREATED)
def crear_servicio(
    servicio_data: ServicioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return registrar_servicio(db, servicio_data, current_user.id_usuario)


@router.get(
    "/asignacion/{id_asignacion}",
    response_model=list[ServicioResponse],
    status_code=status.HTTP_200_OK,
)
def obtener_servicios_por_asignacion(
    id_asignacion: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return listar_servicios_asignacion(db, id_asignacion, current_user.id_usuario)


@router.get("/{id_servicio}", response_model=ServicioResponse, status_code=status.HTTP_200_OK)
def obtener_servicio_por_id(
    id_servicio: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return obtener_servicio(db, id_servicio, current_user.id_usuario)


@router.post(
    "/{id_servicio}/detalles",
    response_model=DetalleServicioResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_detalle_servicio(
    id_servicio: int,
    detalle_data: DetalleServicioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return registrar_detalle_servicio(db, id_servicio, detalle_data, current_user.id_usuario)


@router.get(
    "/{id_servicio}/detalles",
    response_model=list[DetalleServicioResponse],
    status_code=status.HTTP_200_OK,
)
def obtener_detalles_servicio(
    id_servicio: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return listar_detalles_servicio(db, id_servicio, current_user.id_usuario)
