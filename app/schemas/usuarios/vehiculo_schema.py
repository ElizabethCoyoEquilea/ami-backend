from datetime import date

from pydantic import BaseModel, Field, field_validator


class VehiculoBase(BaseModel):
    marca: str = Field(min_length=1, max_length=100)
    anio: int = Field(ge=1900, le=date.today().year + 1)
    modelo: str = Field(min_length=1, max_length=100)
    placa: str = Field(min_length=1, max_length=20)

    @field_validator("marca", "modelo", "placa")
    @classmethod
    def validar_texto_obligatorio(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Este campo es obligatorio")
        return value

    @field_validator("placa")
    @classmethod
    def normalizar_placa(cls, value: str) -> str:
        return value.strip().upper()


class VehiculoCreate(VehiculoBase):
    pass


class VehiculoUpdate(BaseModel):
    marca: str | None = Field(default=None, min_length=1, max_length=100)
    anio: int | None = Field(default=None, ge=1900, le=date.today().year + 1)
    modelo: str | None = Field(default=None, min_length=1, max_length=100)
    placa: str | None = Field(default=None, min_length=1, max_length=20)

    @field_validator("marca", "modelo", "placa")
    @classmethod
    def validar_texto_si_llega(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Este campo no puede estar vacio")
        return value

    @field_validator("placa")
    @classmethod
    def normalizar_placa(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip().upper()


class VehiculoResponse(BaseModel):
    id_vehiculo: int
    id_cliente: int
    marca: str
    anio: int
    modelo: str
    placa: str

    class Config:
        from_attributes = True
