from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.solicitudes.calificacion import Calificacion
from app.schemas.solicitudes.calificacion_schema import CalificacionCreate


def get_calificacion_by_servicio(
    db: Session,
    id_servicio: int,
) -> Calificacion | None:
    return (
        db.query(Calificacion)
        .filter(Calificacion.id_servicio == id_servicio)
        .first()
    )


def create_calificacion(
    db: Session,
    id_servicio: int,
    calificacion_data: CalificacionCreate,
) -> Calificacion:
    try:
        calificacion = Calificacion(
            id_servicio=id_servicio,
            puntuacion=calificacion_data.puntuacion,
            comentario=calificacion_data.comentario,
        )
        db.add(calificacion)
        db.commit()
        db.refresh(calificacion)
        return calificacion
    except SQLAlchemyError:
        db.rollback()
        raise
