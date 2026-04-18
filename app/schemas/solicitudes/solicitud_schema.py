from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class SolicitudCreate(BaseModel):
    id_vehiculo: int = Field(gt=0)
    descripcion: str = Field(min_length=1, max_length=500)
    latitud: float
    direccion: str | None = Field(default=None, max_length=255)
    longitud: float
    audio: str | None = Field(default=None, max_length=1000)
    imagenes: list[str] | None = None

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


class SolicitudResponse(BaseModel):
    id_solicitud: int
    id_vehiculo: int
    descripcion: str
    latitud: float | None
    direccion: str | None
    longitud: float | None
    fecha: datetime
    prioridad: str | None
    observaciones: str | None
    audio: str | None
    imagenes: list[str] | None
    estado: str

    class Config:
        from_attributes = True
