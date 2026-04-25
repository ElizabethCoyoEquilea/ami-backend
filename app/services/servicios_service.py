from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.solicitudes.asignacion import Asignacion
from app.models.solicitudes.servicio import Servicio
from app.repositories.catalogo_servicio_repository import get_active_catalogo_servicio_by_id
from app.repositories.servicios_repository import (
    create_detalle_for_servicio,
    create_servicio_with_detalles,
    get_asignacion_by_id,
    get_servicio_by_id,
    list_detalles_by_servicio,
    list_servicios_by_asignacion,
)
from app.schemas.solicitudes.servicio_schema import DetalleServicioCreate, ServicioCreate


def _validar_asignacion_taller(asignacion: Asignacion, id_usuario: int) -> None:
    if not asignacion.taller or asignacion.taller.id_usuario != id_usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignacion no encontrada para el usuario autenticado",
        )


def _obtener_asignacion_propia(
    db: Session,
    id_asignacion: int,
    id_usuario: int,
) -> Asignacion:
    asignacion = get_asignacion_by_id(db, id_asignacion)
    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignacion no encontrada",
        )
    _validar_asignacion_taller(asignacion, id_usuario)
    return asignacion


def _obtener_servicio_propio(
    db: Session,
    id_servicio: int,
    id_usuario: int,
) -> Servicio:
    servicio = get_servicio_by_id(db, id_servicio)
    if not servicio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )

    asignacion = servicio.asignacion
    if not asignacion or not asignacion.taller or asignacion.taller.id_usuario != id_usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado para el usuario autenticado",
        )

    return servicio


def registrar_servicio(
    db: Session,
    servicio_data: ServicioCreate,
    id_usuario: int,
) -> Servicio:
    _obtener_asignacion_propia(db, servicio_data.id_asignacion, id_usuario)

    for detalle in servicio_data.detalles:
        catalogo = get_active_catalogo_servicio_by_id(db, detalle.id_catalogo_servicio)
        if not catalogo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Catalogo de servicio {detalle.id_catalogo_servicio} no encontrado",
            )

    try:
        return create_servicio_with_detalles(db, servicio_data)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo crear el servicio",
        )


def listar_servicios_asignacion(
    db: Session,
    id_asignacion: int,
    id_usuario: int,
) -> list[Servicio]:
    _obtener_asignacion_propia(db, id_asignacion, id_usuario)
    return list_servicios_by_asignacion(db, id_asignacion)


def obtener_servicio(
    db: Session,
    id_servicio: int,
    id_usuario: int,
) -> Servicio:
    return _obtener_servicio_propio(db, id_servicio, id_usuario)


def registrar_detalle_servicio(
    db: Session,
    id_servicio: int,
    detalle_data: DetalleServicioCreate,
    id_usuario: int,
):
    _obtener_servicio_propio(db, id_servicio, id_usuario)

    catalogo = get_active_catalogo_servicio_by_id(db, detalle_data.id_catalogo_servicio)
    if not catalogo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Catalogo de servicio no encontrado",
        )

    try:
        return create_detalle_for_servicio(db, id_servicio, detalle_data)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo crear el detalle del servicio",
        )


def listar_detalles_servicio(
    db: Session,
    id_servicio: int,
    id_usuario: int,
):
    _obtener_servicio_propio(db, id_servicio, id_usuario)
    return list_detalles_by_servicio(db, id_servicio)
