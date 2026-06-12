from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.solicitudes.solicitud_schema import SolicitudResponse
from app.schemas.solicitudes.servicio_schema import ServicioResponse


class IniciarRecorridoRequest(BaseModel):
    id_taller: int = Field(gt=0)
    id_asignacion: int = Field(gt=0)
    id_solicitud: int = Field(gt=0)
    id_invitacion: int = Field(gt=0)


class IniciarRecorridoResponse(BaseModel):
    id_asignacion: int
    id_solicitud: int
    id_invitacion: int
    id_taller: int
    id_proveedor: int
    estado_asignacion: str
    websocket_enviado: bool


class ConfirmarLlegadaRequest(BaseModel):
    id_taller: int = Field(gt=0)
    id_asignacion: int = Field(gt=0)
    id_solicitud: int = Field(gt=0)
    id_invitacion: int = Field(gt=0)


class ConfirmarLlegadaResponse(BaseModel):
    id_asignacion: int
    id_solicitud: int
    id_invitacion: int
    id_taller: int
    id_proveedor: int
    estado_asignacion: str
    tiempo_llegada: Decimal


class AsignacionConSolicitudResponse(BaseModel):
    id_asignacion: int
    id_invitacion: int | None = None
    id_solicitud: int
    id_taller: int
    id_proveedor: int | None
    fecha_inicio: datetime
    fecha_fin: datetime | None = None
    tiempo_llegada: Decimal | None = None
    estado: str
    solicitud: SolicitudResponse
    servicios: list[ServicioResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True
