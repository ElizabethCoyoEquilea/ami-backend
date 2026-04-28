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
    list_servicios_by_proveedor_usuario,
    list_servicios_by_asignacion,
    list_servicios_by_taller,
)
from app.repositories.talleres_repository import get_active_taller_by_id
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
    es_admin_taller = bool(
        asignacion and asignacion.taller and asignacion.taller.id_usuario == id_usuario
    )
    es_proveedor_asignado = bool(
        asignacion
        and asignacion.proveedor_servicio
        and asignacion.proveedor_servicio.id_usuario == id_usuario
    )
    if not es_admin_taller and not es_proveedor_asignado:
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


def listar_servicios_proveedor_actual(
    db: Session,
    id_usuario: int,
) -> list[Servicio]:
    return list_servicios_by_proveedor_usuario(db, id_usuario)


def listar_servicios_taller(
    db: Session,
    id_taller: int,
) -> list[Servicio]:
    taller = get_active_taller_by_id(db, id_taller)
    if not taller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taller no encontrado",
        )

    return list_servicios_by_taller(db, id_taller)


def obtener_servicio(
    db: Session,
    id_servicio: int,
) -> Servicio:
    servicio = get_servicio_by_id(db, id_servicio)
    if not servicio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )

    return servicio


def registrar_detalle_servicio(
    db: Session,
    id_servicio: int,
    detalles_data: list[DetalleServicioCreate],
    id_usuario: int,
):
    _obtener_servicio_propio(db, id_servicio, id_usuario)

    if not detalles_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe enviar al menos un detalle de servicio",
        )

    for detalle_data in detalles_data:
        catalogo = get_active_catalogo_servicio_by_id(db, detalle_data.id_catalogo_servicio)
        if not catalogo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Catalogo de servicio {detalle_data.id_catalogo_servicio} no encontrado",
            )

    try:
        servicio_actualizado = create_detalle_for_servicio(db, id_servicio, detalles_data)
        return {
            "servicio": servicio_actualizado,
            "detalles": servicio_actualizado.detalles_servicio,
            "pago": servicio_actualizado.pago,
            "total": servicio_actualizado.total,
        }
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo crear el detalle del servicio",
        )


def listar_detalles_servicio(
    db: Session,
    id_servicio: int,
):
    servicio = get_servicio_by_id(db, id_servicio)
    if not servicio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )

    return list_detalles_by_servicio(db, id_servicio)
