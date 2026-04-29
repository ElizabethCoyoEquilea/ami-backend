from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuarios.usuario import User
from app.schemas.solicitudes.servicio_schema import (
    DetalleServicioCreate,
    DetalleServicioResponse,
    ServicioCreate,
    ServicioFacturaResponse,
    ServicioResponse,
    ServicioResumenResponse,
)
from app.services.servicios_service import (
    anular_servicio,
    listar_detalles_servicio,
    listar_servicios_proveedor_actual,
    listar_servicios_asignacion,
    listar_servicios_taller,
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


@router.get(
    "/proveedor/mis-servicios",
    response_model=list[ServicioResponse],
    status_code=status.HTTP_200_OK,
)
def obtener_mis_servicios_proveedor(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return listar_servicios_proveedor_actual(db, current_user.id_usuario)


@router.get(
    "/taller/{id_taller}",
    response_model=list[ServicioResumenResponse],
    status_code=status.HTTP_200_OK,
)
def obtener_servicios_taller(
    id_taller: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return listar_servicios_taller(db, id_taller)


@router.get("/{id_servicio}", response_model=ServicioResponse, status_code=status.HTTP_200_OK)
def obtener_servicio_por_id(
    id_servicio: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return obtener_servicio(db, id_servicio)


@router.patch(
    "/{id_servicio}/anularservicio",
    response_model=ServicioResponse,
    status_code=status.HTTP_200_OK,
)
def anular_servicio_por_id(
    id_servicio: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return anular_servicio(db, id_servicio)


@router.post(
    "/{id_servicio}/detalles",
    response_model=ServicioFacturaResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_detalle_servicio(
    id_servicio: int,
    detalles_data: list[DetalleServicioCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return registrar_detalle_servicio(db, id_servicio, detalles_data, current_user.id_usuario)


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
    return listar_detalles_servicio(db, id_servicio)
