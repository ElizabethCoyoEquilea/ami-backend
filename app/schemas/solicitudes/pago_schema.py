from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class PagoResponse(BaseModel):
    id_pago: int
    monto: float
    estado: str
    metodo: str | None
    fecha: datetime | None

    class Config:
        from_attributes = True


class PagoUpdate(BaseModel):
    monto: float | None = Field(default=None, ge=0)
    estado: str | None = Field(default=None, max_length=30)
    metodo: str | None = Field(default=None, max_length=50)
    fecha: datetime | None = None

    @field_validator("estado", "metodo")
    @classmethod
    def limpiar_texto_opcional(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None
