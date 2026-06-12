from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class SolicitudCreate(BaseModel):
    id_vehiculo: int = Field(gt=0)
    id_zona: int | None = Field(default=None, gt=0)
    descripcion: str = Field(min_length=1, max_length=500)
    latitud: float
    direccion: str | None = Field(default=None, max_length=255)
    longitud: float
    audio: str | None = Field(default=None, max_length=1000)
    imagenes: list[str] | None = None
    ronda_actual: int = Field(default=1, ge=1)

    @field_validator("descripcion")
    @classmethod
    def validar_descripcion(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("La descripcion es obligatoria")
        return value

    @field_validator("direccion", "audio")
    @classmethod
    def limpiar_texto_opcional(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None


class SolicitudAsignacionResponse(BaseModel):
    id_asignacion: int
    id_solicitud: int
    id_taller: int
    id_proveedor: int | None
    fecha_inicio: datetime
    fecha_fin: datetime | None = None
    tiempo_llegada: Decimal | None = None
    estado: str

    class Config:
        from_attributes = True


class CancelarSolicitudRequest(BaseModel):
    id_solicitud: int = Field(gt=0)


class SolicitudInvitacionCanceladaResponse(BaseModel):
    id_invitacion: int
    id_solicitud: int
    id_taller: int
    estado: str

    class Config:
        from_attributes = True


class CancelarSolicitudResponse(BaseModel):
    id_solicitud: int
    estado: str
    invitaciones: list[SolicitudInvitacionCanceladaResponse]


class SolicitudResponse(BaseModel):
    id_solicitud: int
    id_vehiculo: int
    id_zona: int | None
    descripcion: str
    latitud: float | None
    direccion: str | None
    longitud: float | None
    fecha: datetime
    prioridad: str | None
    observaciones: str | None
    audio: str | None
    imagenes: list[str] | None
    ronda_actual: int
    estado: str
    recomendacion: str | None = None
    distancia_desde_taller: float | None = None
    asignacion: SolicitudAsignacionResponse | None = None

    class Config:
        from_attributes = True
