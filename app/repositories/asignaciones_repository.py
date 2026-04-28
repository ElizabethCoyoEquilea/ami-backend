from sqlalchemy.orm import Session, joinedload

from app.models.solicitudes.asignacion import Asignacion
from app.models.solicitudes.detalle_servicio import DetalleServicio
from app.models.solicitudes.solicitud import Solicitud
from app.models.solicitudes.servicio import Servicio
from app.models.usuarios.vehiculo import Vehiculo


def get_asignacion_detalle_by_id(
    db: Session,
    id_asignacion: int,
) -> Asignacion | None:
    return (
        db.query(Asignacion)
        .options(
            joinedload(Asignacion.taller),
            joinedload(Asignacion.proveedor_servicio),
            joinedload(Asignacion.solicitud)
            .joinedload(Solicitud.vehiculo)
            .joinedload(Vehiculo.cliente),
            joinedload(Asignacion.servicios)
            .joinedload(Servicio.detalles_servicio)
            .joinedload(DetalleServicio.catalogo_servicio),
        )
        .filter(Asignacion.id_asignacion == id_asignacion)
        .first()
    )
