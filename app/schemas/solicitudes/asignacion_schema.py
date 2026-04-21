from datetime import datetime

from pydantic import BaseModel

from app.schemas.solicitudes.solicitud_schema import SolicitudResponse


class AsignacionConSolicitudResponse(BaseModel):
    id_asignacion: int
    id_solicitud: int
    id_taller: int
    id_catalogo_servicio: int | None
    fecha: datetime
    estado: str
    solicitud: SolicitudResponse

    class Config:
        from_attributes = True
