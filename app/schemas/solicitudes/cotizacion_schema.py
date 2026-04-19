from pydantic import BaseModel

from app.schemas.solicitudes.solicitud_schema import SolicitudResponse


class CotizacionResponse(BaseModel):
    id_cotizacion: int
    id_solicitud: int
    id_taller: int
    monto: float
    estado: str

    class Config:
        from_attributes = True


class CotizacionConSolicitudResponse(CotizacionResponse):
    solicitud: SolicitudResponse


class CotizacionMontoEnviadoResponse(CotizacionResponse):
    websocket_enviado: bool


class CotizacionRechazoAdministradorResponse(CotizacionResponse):
    websocket_enviado: bool
