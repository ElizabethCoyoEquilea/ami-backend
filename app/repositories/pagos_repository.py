from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.solicitudes.asignacion import Asignacion
from app.models.solicitudes.pago import Pago
from app.models.solicitudes.servicio import Servicio
from app.models.usuarios.proveedor_servicio import ProveedorServicio
from app.schemas.solicitudes.pago_schema import PagoUpdate


def get_pago_by_id(db: Session, id_pago: int) -> Pago | None:
    return db.query(Pago).filter(Pago.id_pago == id_pago).first()


def update_pago(db: Session, pago: Pago, pago_data: PagoUpdate) -> Pago:
    try:
        update_data = pago_data.model_dump(exclude_unset=True)
        if "monto" in update_data and update_data["monto"] is not None:
            update_data["monto"] = Decimal(str(update_data["monto"]))

        for field, value in update_data.items():
            setattr(pago, field, value)

        servicio = db.query(Servicio).filter(Servicio.id_pago == pago.id_pago).first()
        if servicio:
            servicio.estado = "pagado"
            proveedor = (
                db.query(ProveedorServicio)
                .join(Asignacion, Asignacion.id_proveedor == ProveedorServicio.id_proveedor)
                .filter(Asignacion.id_asignacion == servicio.id_asignacion)
                .first()
            )
            if proveedor:
                proveedor.estado = "Disponible"

        db.commit()
        db.refresh(pago)
        return pago
    except SQLAlchemyError:
        db.rollback()
        raise
