from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class CalificacionCreate(BaseModel):
    puntuacion: int = Field(ge=1, le=5)
    comentario: str | None = Field(default=None, max_length=500)

    @field_validator("comentario")
    @classmethod
    def limpiar_comentario(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None


class CalificacionResponse(BaseModel):
    id_calificacion: int
    id_servicio: int
    puntuacion: int
    comentario: str | None
    fecha: datetime

    class Config:
        from_attributes = True


class ServicioTieneCalificacionResponse(BaseModel):
    id_servicio: int
    tiene_calificacion: bool
