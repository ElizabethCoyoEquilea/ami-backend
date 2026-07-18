from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.repositories.calificaciones_cliente_repository import (
    create_calificacion_cliente,
    get_calificacion_cliente_by_servicio,
    get_promedio_y_total_calificaciones_cliente,
    list_calificaciones_cliente,
)
from app.repositories.servicios_repository import get_servicio_by_id
from app.schemas.solicitudes.calificacion_cliente_schema import CalificacionClienteCreate


def registrar_calificacion_cliente(
    db: Session,
    id_servicio: int,
    calificacion_data: CalificacionClienteCreate,
    id_usuario_actual: int,
):
    servicio = get_servicio_by_id(db, id_servicio)
    if not servicio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )

    # Validar que el servicio este finalizado o pagado
    if servicio.estado.lower() not in ("pagado", "finalizado"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo puede calificarse un servicio finalizado/pagado",
        )

    # Validar que no se haya calificado antes
    calificacion_existente = get_calificacion_cliente_by_servicio(db, id_servicio)
    if calificacion_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este servicio ya cuenta con una calificacion del cliente",
        )

    # Validar que el usuario sea el proveedor asignado
    asignacion = servicio.asignacion
    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El servicio no cuenta con una asignacion valida",
        )

    proveedor = asignacion.proveedor_servicio
    if not proveedor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El servicio no tiene un proveedor asignado",
        )

    if proveedor.id_usuario != id_usuario_actual:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el proveedor asignado al servicio puede calificar al cliente",
        )

    # Buscar el cliente asociado al servicio
    solicitud = asignacion.solicitud
    if not solicitud or not solicitud.vehiculo or not solicitud.vehiculo.cliente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo encontrar al cliente asociado a este servicio",
        )

    id_cliente = solicitud.vehiculo.cliente.id_cliente

    try:
        return create_calificacion_cliente(db, id_servicio, id_cliente, calificacion_data)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo registrar la calificacion del cliente",
        )


def servicio_tiene_calificacion_cliente(
    db: Session,
    id_servicio: int,
) -> dict:
    servicio = get_servicio_by_id(db, id_servicio)
    if not servicio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )

    calificacion = get_calificacion_cliente_by_servicio(db, id_servicio)
    return {
        "id_servicio": id_servicio,
        "tiene_calificacion_cliente": calificacion is not None,
    }


def obtener_historial_calificaciones_cliente(
    db: Session,
    id_cliente: int,
):
    return list_calificaciones_cliente(db, id_cliente)


def obtener_promedio_y_total_cliente(
    db: Session,
    id_cliente: int,
) -> dict:
    promedio, total = get_promedio_y_total_calificaciones_cliente(db, id_cliente)
    return {
        "id_cliente": id_cliente,
        "promedio": promedio,
        "total_calificaciones": total,
    }
