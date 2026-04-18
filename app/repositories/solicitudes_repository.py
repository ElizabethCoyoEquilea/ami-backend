from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.solicitudes.solicitud import Solicitud
from app.schemas.solicitudes.solicitud_schema import SolicitudCreate


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
