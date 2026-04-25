from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.models.solicitudes.asignacion import Asignacion
from app.models.solicitudes.cotizacion import Cotizacion
from app.models.solicitudes.solicitud import Solicitud
from app.models.usuarios.vehiculo import Vehiculo


def get_cotizacion_finalizada_by_solicitud(
    db: Session,
    id_solicitud: int,
) -> Cotizacion | None:
    return (
        db.query(Cotizacion)
        .filter(
            Cotizacion.id_solicitud == id_solicitud,
            Cotizacion.estado.in_(["aceptada", "aceptado", "rechazada", "rechazado"]),
        )
        .first()
    )


def get_cotizacion_detalle_by_id(
    db: Session,
    id_cotizacion: int,
) -> Cotizacion | None:
    return (
        db.query(Cotizacion)
        .options(
            joinedload(Cotizacion.solicitud)
            .joinedload(Solicitud.vehiculo)
            .joinedload(Vehiculo.cliente),
            joinedload(Cotizacion.taller),
        )
        .filter(Cotizacion.id_cotizacion == id_cotizacion)
        .first()
    )


def create_cotizacion_pendiente(
    db: Session,
    solicitud: Solicitud,
    id_taller: int,
) -> Cotizacion:
    try:
        cotizacion = Cotizacion(
            id_solicitud=solicitud.id_solicitud,
            id_taller=id_taller,
            monto=Decimal("0.00"),
            estado="pendiente",
        )
        solicitud.estado = "enviado"
        db.add(cotizacion)
        db.commit()
        db.refresh(cotizacion)
        return cotizacion
    except SQLAlchemyError:
        db.rollback()
        raise


def update_monto_cotizacion_admin(
    db: Session,
    cotizacion: Cotizacion,
    monto: Decimal,
) -> Cotizacion:
    try:
        cotizacion.monto = monto
        db.commit()
        db.refresh(cotizacion)
        return cotizacion
    except SQLAlchemyError:
        db.rollback()
        raise


def aceptar_cotizacion_cliente(
    db: Session,
    cotizacion: Cotizacion,
) -> Asignacion:
    try:
        cotizacion.estado = "aceptada"
        cotizacion.solicitud.estado = "aceptada"

        asignacion = Asignacion(
            id_solicitud=cotizacion.id_solicitud,
            id_taller=cotizacion.id_taller,
            estado="Pendiente de asignar personal",
        )
        db.add(asignacion)
        db.commit()
        db.refresh(asignacion)
        return asignacion
    except SQLAlchemyError:
        db.rollback()
        raise


def rechazar_cotizacion_cliente(
    db: Session,
    cotizacion: Cotizacion,
) -> Cotizacion:
    try:
        cotizacion.estado = "rechazada"
        cotizacion.solicitud.estado = "pendiente"
        db.commit()
        db.refresh(cotizacion)
        return cotizacion
    except SQLAlchemyError:
        db.rollback()
        raise


def list_cotizaciones_pendientes_by_taller(
    db: Session,
    id_taller: int,
) -> list[Cotizacion]:
    return (
        db.query(Cotizacion)
        .options(joinedload(Cotizacion.solicitud))
        .filter(
            Cotizacion.id_taller == id_taller,
            Cotizacion.estado == "pendiente",
        )
        .order_by(Cotizacion.id_cotizacion)
        .all()
    )
