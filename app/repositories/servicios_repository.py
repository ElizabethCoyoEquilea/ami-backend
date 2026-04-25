from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.models.solicitudes.asignacion import Asignacion
from app.models.solicitudes.detalle_servicio import DetalleServicio
from app.models.solicitudes.servicio import Servicio
from app.schemas.solicitudes.servicio_schema import DetalleServicioCreate, ServicioCreate


def get_asignacion_by_id(db: Session, id_asignacion: int) -> Asignacion | None:
    return (
        db.query(Asignacion)
        .options(joinedload(Asignacion.taller))
        .filter(Asignacion.id_asignacion == id_asignacion)
        .first()
    )


def get_servicio_by_id(db: Session, id_servicio: int) -> Servicio | None:
    return (
        db.query(Servicio)
        .options(
            joinedload(Servicio.asignacion).joinedload(Asignacion.taller),
            joinedload(Servicio.detalles_servicio).joinedload(DetalleServicio.catalogo_servicio),
        )
        .filter(Servicio.id_servicio == id_servicio)
        .first()
    )


def list_servicios_by_asignacion(db: Session, id_asignacion: int) -> list[Servicio]:
    return (
        db.query(Servicio)
        .options(joinedload(Servicio.detalles_servicio).joinedload(DetalleServicio.catalogo_servicio))
        .filter(Servicio.id_asignacion == id_asignacion)
        .order_by(Servicio.id_servicio)
        .all()
    )


def create_servicio_with_detalles(
    db: Session,
    servicio_data: ServicioCreate,
) -> Servicio:
    try:
        servicio = Servicio(
            id_asignacion=servicio_data.id_asignacion,
            total=Decimal(str(servicio_data.total)) if servicio_data.total is not None else Decimal("0.00"),
            fecha_inicio=servicio_data.fecha_inicio,
            fecha_fin=servicio_data.fecha_fin,
            estado=servicio_data.estado or "pendiente",
        )
        db.add(servicio)
        db.flush()

        total_calculado = Decimal("0.00")
        for detalle_data in servicio_data.detalles:
            precio = Decimal(str(detalle_data.precio))
            sub_total = precio * Decimal(detalle_data.cantidad)
            total_calculado += sub_total

            detalle = DetalleServicio(
                id_servicio=servicio.id_servicio,
                id_catalogo_servicio=detalle_data.id_catalogo_servicio,
                cantidad=detalle_data.cantidad,
                precio=precio,
                sub_total=sub_total,
                nombre=detalle_data.nombre,
                descripcion=detalle_data.descripcion,
            )
            db.add(detalle)

        if servicio_data.total is None:
            servicio.total = total_calculado

        db.commit()
        db.refresh(servicio)
        return servicio
    except SQLAlchemyError:
        db.rollback()
        raise


def create_detalle_for_servicio(
    db: Session,
    id_servicio: int,
    detalle_data: DetalleServicioCreate,
) -> DetalleServicio:
    try:
        precio = Decimal(str(detalle_data.precio))
        sub_total = precio * Decimal(detalle_data.cantidad)

        detalle = DetalleServicio(
            id_servicio=id_servicio,
            id_catalogo_servicio=detalle_data.id_catalogo_servicio,
            cantidad=detalle_data.cantidad,
            precio=precio,
            sub_total=sub_total,
            nombre=detalle_data.nombre,
            descripcion=detalle_data.descripcion,
        )
        db.add(detalle)
        db.flush()

        total_servicio = (
            db.query(func.coalesce(func.sum(DetalleServicio.sub_total), 0))
            .filter(DetalleServicio.id_servicio == id_servicio)
            .scalar()
        )

        servicio = db.query(Servicio).filter(Servicio.id_servicio == id_servicio).first()
        if servicio:
            servicio.total = total_servicio

        db.commit()
        db.refresh(detalle)
        return detalle
    except SQLAlchemyError:
        db.rollback()
        raise


def list_detalles_by_servicio(db: Session, id_servicio: int) -> list[DetalleServicio]:
    return (
        db.query(DetalleServicio)
        .options(joinedload(DetalleServicio.catalogo_servicio))
        .filter(DetalleServicio.id_servicio == id_servicio)
        .order_by(DetalleServicio.id_detalle_servicio)
        .all()
    )
