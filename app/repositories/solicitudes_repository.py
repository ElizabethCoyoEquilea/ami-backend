from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

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


def create_solicitud(
    db: Session,
    solicitud_data: SolicitudCreate,
    estado: str = "pendiente",
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
