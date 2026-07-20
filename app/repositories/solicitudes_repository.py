from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.models.solicitudes.cotizacion import Invitacion
from app.models.solicitudes.solicitud import Solicitud
from app.models.usuarios.cliente import Cliente
from app.models.usuarios.vehiculo import Vehiculo
from app.schemas.solicitudes.solicitud_schema import SolicitudCreate


def get_solicitud_by_id(db: Session, id_solicitud: int) -> Solicitud | None:
    return db.query(Solicitud).filter(Solicitud.id_solicitud == id_solicitud).first()


def get_solicitud_by_id_for_user(
    db: Session,
    id_solicitud: int,
    id_usuario: int,
) -> Solicitud | None:
    return (
        db.query(Solicitud)
        .join(Vehiculo, Vehiculo.id_vehiculo == Solicitud.id_vehiculo)
        .join(Cliente, Cliente.id_cliente == Vehiculo.id_cliente)
        .filter(
            Solicitud.id_solicitud == id_solicitud,
            Cliente.id_usuario == id_usuario,
        )
        .first()
    )


def list_solicitudes_by_user(
    db: Session,
    id_usuario: int,
) -> list[Solicitud]:
    return (
        db.query(Solicitud)
        .options(joinedload(Solicitud.asignaciones))
        .join(Vehiculo, Vehiculo.id_vehiculo == Solicitud.id_vehiculo)
        .join(Cliente, Cliente.id_cliente == Vehiculo.id_cliente)
        .filter(Cliente.id_usuario == id_usuario)
        .order_by(Solicitud.fecha.desc(), Solicitud.id_solicitud.desc())
        .all()
    )


def list_solicitudes_by_taller(
    db: Session,
    id_taller: int,
) -> list[Solicitud]:
    return (
        db.query(Solicitud)
        .join(Invitacion, Invitacion.id_solicitud == Solicitud.id_solicitud)
        .filter(Invitacion.id_taller == id_taller)
        .order_by(Solicitud.fecha.desc(), Solicitud.id_solicitud.desc())
        .all()
    )


def list_invitaciones_con_solicitud_by_taller(
    db: Session,
    id_taller: int,
) -> list[Invitacion]:
    return (
        db.query(Invitacion)
        .join(Solicitud, Solicitud.id_solicitud == Invitacion.id_solicitud)
        .options(joinedload(Invitacion.solicitud))
        .filter(Invitacion.id_taller == id_taller)
        .order_by(Solicitud.fecha.desc(), Solicitud.id_solicitud.desc())
        .all()
    )


def create_solicitud(
    db: Session,
    solicitud_data: SolicitudCreate,
    estado: str = "buscando_taller",
) -> Solicitud:
    try:
        solicitud = Solicitud(
            **solicitud_data.model_dump(),
            estado=estado,
        )
        db.add(solicitud)
        db.commit()
        db.refresh(solicitud)
        return solicitud
    except SQLAlchemyError:
        db.rollback()
        raise


def update_solicitud_ai_analysis(
    db: Session,
    solicitud: Solicitud,
    prioridad: str | None,
    observaciones: str | None,
    recomendacion: str | None,
) -> Solicitud:
    try:
        solicitud.prioridad = prioridad
        solicitud.observaciones = observaciones
        solicitud.recomendacion = recomendacion
        db.commit()
        db.refresh(solicitud)
        return solicitud
    except SQLAlchemyError:
        db.rollback()
        raise


def update_solicitud_recomendacion(
    db: Session,
    solicitud: Solicitud,
    recomendacion: str,
) -> Solicitud:
    try:
        solicitud.recomendacion = recomendacion
        db.commit()
        db.refresh(solicitud)
        return solicitud
    except SQLAlchemyError:
        db.rollback()
        raise


def update_solicitud_fallback(
    db: Session,
    solicitud: Solicitud,
    recomendacion: str,
    prioridad: str,
) -> Solicitud:
    try:
        solicitud.recomendacion = recomendacion
        solicitud.prioridad = prioridad
        db.commit()
        db.refresh(solicitud)
        return solicitud
    except SQLAlchemyError:
        db.rollback()
        raise
