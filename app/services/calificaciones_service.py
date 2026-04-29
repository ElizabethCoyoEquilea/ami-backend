from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.repositories.calificaciones_repository import (
    create_calificacion,
    get_calificacion_by_servicio,
)
from app.repositories.servicios_repository import get_servicio_by_id
from app.schemas.solicitudes.calificacion_schema import CalificacionCreate


def registrar_calificacion_servicio(
    db: Session,
    id_servicio: int,
    calificacion_data: CalificacionCreate,
):
    servicio = get_servicio_by_id(db, id_servicio)
    if not servicio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )

    calificacion_existente = get_calificacion_by_servicio(db, id_servicio)
    if calificacion_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El servicio ya tiene una calificacion registrada",
        )

    try:
        return create_calificacion(db, id_servicio, calificacion_data)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo registrar la calificacion",
        )


def servicio_tiene_calificacion(
    db: Session,
    id_servicio: int,
) -> dict:
    servicio = get_servicio_by_id(db, id_servicio)
    if not servicio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado",
        )

    calificacion = get_calificacion_by_servicio(db, id_servicio)
    return {
        "id_servicio": id_servicio,
        "tiene_calificacion": calificacion is not None,
    }
