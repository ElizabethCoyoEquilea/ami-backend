from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.solicitudes.calificacion_cliente import CalificacionCliente
from app.schemas.solicitudes.calificacion_cliente_schema import CalificacionClienteCreate


def get_calificacion_cliente_by_servicio(
    db: Session,
    id_servicio: int,
) -> CalificacionCliente | None:
    return (
        db.query(CalificacionCliente)
        .filter(CalificacionCliente.id_servicio == id_servicio)
        .first()
    )


def create_calificacion_cliente(
    db: Session,
    id_servicio: int,
    id_cliente: int,
    calificacion_data: CalificacionClienteCreate,
) -> CalificacionCliente:
    try:
        calificacion = CalificacionCliente(
            id_servicio=id_servicio,
            id_cliente=id_cliente,
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


def list_calificaciones_cliente(
    db: Session,
    id_cliente: int,
) -> list[CalificacionCliente]:
    return (
        db.query(CalificacionCliente)
        .filter(CalificacionCliente.id_cliente == id_cliente)
        .order_by(CalificacionCliente.fecha.desc())
        .all()
    )


def get_promedio_y_total_calificaciones_cliente(
    db: Session,
    id_cliente: int,
) -> tuple[float, int]:
    result = (
        db.query(
            func.avg(CalificacionCliente.puntuacion),
            func.count(CalificacionCliente.id_calificacion_cliente),
        )
        .filter(CalificacionCliente.id_cliente == id_cliente)
        .first()
    )
    promedio = float(result[0]) if result and result[0] is not None else 0.0
    total = int(result[1]) if result and result[1] is not None else 0
    return promedio, total
