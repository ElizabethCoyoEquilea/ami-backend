from datetime import datetime

from pydantic import BaseModel

from app.schemas.solicitudes.solicitud_schema import SolicitudResponse


class InvitacionResponse(BaseModel):
    id_invitacion: int
    id_solicitud: int
    id_taller: int
    numero_ronda: int
    estado: str
    fecha_hora_envio: datetime
    fecha_hora_expiracion: datetime | None
    fecha_hora_respuesta: datetime | None

    class Config:
        from_attributes = True


class InvitacionConSolicitudResponse(InvitacionResponse):
    solicitud: SolicitudResponse


class InvitacionRechazoAdministradorResponse(InvitacionResponse):
    websocket_enviado: bool
