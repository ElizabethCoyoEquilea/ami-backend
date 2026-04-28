from datetime import datetime
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.models.solicitudes.asignacion import Asignacion
from app.models.solicitudes.detalle_servicio import DetalleServicio
from app.models.solicitudes.pago import Pago
from app.models.solicitudes.solicitud import Solicitud
from app.models.solicitudes.servicio import Servicio
from app.models.usuarios.vehiculo import Vehiculo
from app.models.usuarios.proveedor_servicio import ProveedorServicio
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
            joinedload(Servicio.asignacion)
            .joinedload(Asignacion.solicitud)
            .joinedload(Solicitud.vehiculo)
            .joinedload(Vehiculo.cliente),
            joinedload(Servicio.pago),
            joinedload(Servicio.detalles_servicio).joinedload(DetalleServicio.catalogo_servicio),
        )
        .filter(Servicio.id_servicio == id_servicio)
        .first()
    )


def list_servicios_by_asignacion(db: Session, id_asignacion: int) -> list[Servicio]:
    return (
        db.query(Servicio)
        .options(
            joinedload(Servicio.asignacion)
            .joinedload(Asignacion.solicitud)
            .joinedload(Solicitud.vehiculo)
            .joinedload(Vehiculo.cliente),
            joinedload(Servicio.pago),
            joinedload(Servicio.detalles_servicio).joinedload(DetalleServicio.catalogo_servicio),
        )
        .filter(Servicio.id_asignacion == id_asignacion)
        .order_by(Servicio.id_servicio)
        .all()
    )


def list_servicios_by_taller(
    db: Session,
    id_taller: int,
) -> list[Servicio]:
    return (
        db.query(Servicio)
        .join(Asignacion, Asignacion.id_asignacion == Servicio.id_asignacion)
        .options(
            joinedload(Servicio.asignacion).joinedload(Asignacion.taller),
            joinedload(Servicio.asignacion)
            .joinedload(Asignacion.solicitud)
            .joinedload(Solicitud.vehiculo)
            .joinedload(Vehiculo.cliente),
            joinedload(Servicio.pago),
            joinedload(Servicio.detalles_servicio).joinedload(DetalleServicio.catalogo_servicio),
        )
        .filter(Asignacion.id_taller == id_taller)
        .order_by(Servicio.id_servicio)
        .all()
    )


def list_servicios_by_proveedor_usuario(
    db: Session,
    id_usuario: int,
) -> list[Servicio]:
    return (
        db.query(Servicio)
        .join(Asignacion, Asignacion.id_asignacion == Servicio.id_asignacion)
        .join(
            ProveedorServicio,
            ProveedorServicio.id_proveedor == Asignacion.id_proveedor,
        )
        .options(
            joinedload(Servicio.asignacion).joinedload(Asignacion.taller),
            joinedload(Servicio.asignacion)
            .joinedload(Asignacion.solicitud)
            .joinedload(Solicitud.vehiculo)
            .joinedload(Vehiculo.cliente),
            joinedload(Servicio.pago),
            joinedload(Servicio.detalles_servicio).joinedload(DetalleServicio.catalogo_servicio),
        )
        .filter(ProveedorServicio.id_usuario == id_usuario)
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
                observacion=detalle_data.observacion,
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
    detalles_data: list[DetalleServicioCreate],
) -> Servicio:
    try:
        for detalle_data in detalles_data:
            precio = Decimal(str(detalle_data.precio))
            sub_total = precio * Decimal(detalle_data.cantidad)

            detalle = DetalleServicio(
                id_servicio=id_servicio,
                id_catalogo_servicio=detalle_data.id_catalogo_servicio,
                cantidad=detalle_data.cantidad,
                precio=precio,
                sub_total=sub_total,
                nombre=detalle_data.nombre,
                observacion=detalle_data.observacion,
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
            servicio.fecha_fin = datetime.now()
            servicio.estado = "Pendiente de pago"
            if servicio.pago:
                servicio.pago.monto = total_servicio
                servicio.pago.estado = "pendiente"
                servicio.pago.fecha = None
            else:
                pago = Pago(
                    monto=total_servicio,
                    estado="pendiente",
                    metodo=None,
                    fecha=None,
                )
                db.add(pago)
                db.flush()
                servicio.id_pago = pago.id_pago

        db.commit()
        servicio_actualizado = get_servicio_by_id(db, id_servicio)
        if servicio_actualizado is None:
            raise SQLAlchemyError("Servicio no encontrado despues de crear detalle")
        return servicio_actualizado
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
