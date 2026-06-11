from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.models.solicitudes.asignacion import Asignacion
from app.models.solicitudes.cotizacion import Invitacion
from app.models.solicitudes.solicitud import Solicitud
from app.models.usuarios.vehiculo import Vehiculo


def get_invitacion_finalizada_by_solicitud(
    db: Session,
    id_solicitud: int,
) -> Invitacion | None:
    return (
        db.query(Invitacion)
        .filter(
            Invitacion.id_solicitud == id_solicitud,
            Invitacion.estado.in_(["aceptada", "aceptado", "rechazada", "rechazado"]),
        )
        .first()
    )


def get_invitacion_detalle_by_id(
    db: Session,
    id_invitacion: int,
) -> Invitacion | None:
    return (
        db.query(Invitacion)
        .options(
            joinedload(Invitacion.solicitud)
            .joinedload(Solicitud.vehiculo)
            .joinedload(Vehiculo.cliente),
            joinedload(Invitacion.taller),
        )
        .filter(Invitacion.id_invitacion == id_invitacion)
        .first()
    )


def create_invitacion_pendiente(
    db: Session,
    solicitud: Solicitud,
    id_taller: int,
) -> Invitacion:
    try:
        invitacion = Invitacion(
            id_solicitud=solicitud.id_solicitud,
            id_taller=id_taller,
            numero_ronda=solicitud.ronda_actual or 1,
            estado="pendiente",
        )
        solicitud.estado = "enviado"
        db.add(invitacion)
        db.commit()
        db.refresh(invitacion)
        return invitacion
    except SQLAlchemyError:
        db.rollback()
        raise


def aceptar_invitacion_cliente(
    db: Session,
    invitacion: Invitacion,
) -> Asignacion:
    try:
        invitacion.estado = "aceptada"
        invitacion.fecha_hora_respuesta = datetime.now()
        invitacion.solicitud.estado = "aceptada"

        asignacion = Asignacion(
            id_solicitud=invitacion.id_solicitud,
            id_taller=invitacion.id_taller,
            id_proveedor=None,
            estado="Pendiente de asignar personal",
        )
        db.add(asignacion)
        db.commit()
        db.refresh(asignacion)
        return asignacion
    except SQLAlchemyError:
        db.rollback()
        raise


def rechazar_invitacion_cliente(
    db: Session,
    invitacion: Invitacion,
) -> Invitacion:
    try:
        invitacion.estado = "rechazada"
        invitacion.fecha_hora_respuesta = datetime.now()
        invitacion.solicitud.estado = "pendiente"
        db.commit()
        db.refresh(invitacion)
        return invitacion
    except SQLAlchemyError:
        db.rollback()
        raise


def list_invitaciones_pendientes_by_taller(
    db: Session,
    id_taller: int,
) -> list[Invitacion]:
    return (
        db.query(Invitacion)
        .options(joinedload(Invitacion.solicitud))
        .filter(
            Invitacion.id_taller == id_taller,
            Invitacion.estado == "pendiente",
        )
        .order_by(Invitacion.id_invitacion)
        .all()
    )
