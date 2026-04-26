from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.solicitudes.asignacion import Asignacion
from app.repositories.asignaciones_repository import get_asignacion_detalle_by_id


def obtener_asignacion_por_id(
    db: Session,
    id_asignacion: int,
) -> Asignacion:
    asignacion = get_asignacion_detalle_by_id(db, id_asignacion)
    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignacion no encontrada",
        )

    return asignacion
