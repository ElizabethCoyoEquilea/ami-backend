from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.solicitudes.solicitud_schema import SolicitudResponse
from app.schemas.solicitudes.servicio_schema import ServicioResponse


class AsignacionConSolicitudResponse(BaseModel):
    id_asignacion: int
    id_invitacion: int | None = None
    id_solicitud: int
    id_taller: int
    id_proveedor: int | None
    fecha: datetime
    estado: str
    solicitud: SolicitudResponse
    servicios: list[ServicioResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True
