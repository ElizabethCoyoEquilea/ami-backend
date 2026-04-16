from datetime import datetime

from pydantic import BaseModel, Field, field_validator


ESTADOS_CATALOGO_SERVICIO = {"activo", "inactivo"}


class CatalogoServicioBase(BaseModel):
    id_taller: int = Field(gt=0)
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str | None = Field(default=None, max_length=500)
    categoria: str = Field(min_length=1, max_length=100)
    unidad_medida: str = Field(min_length=1, max_length=50)
    precio_estandar: float = Field(ge=0)

    @field_validator("nombre", "categoria", "unidad_medida")
    @classmethod
    def validar_texto_obligatorio(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Este campo es obligatorio")
        return value

    @field_validator("descripcion")
    @classmethod
    def limpiar_descripcion(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None


class CatalogoServicioCreate(CatalogoServicioBase):
    pass


class CatalogoServicioUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    descripcion: str | None = Field(default=None, max_length=500)
    categoria: str | None = Field(default=None, min_length=1, max_length=100)
    unidad_medida: str | None = Field(default=None, min_length=1, max_length=50)
    precio_estandar: float | None = Field(default=None, ge=0)
    estado: str | None = None

    @field_validator("nombre", "categoria", "unidad_medida")
    @classmethod
    def validar_texto_si_llega(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Este campo no puede estar vacio")
        return value

    @field_validator("descripcion")
    @classmethod
    def limpiar_descripcion(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None

    @field_validator("estado")
    @classmethod
    def validar_estado(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip().lower()
        if value not in ESTADOS_CATALOGO_SERVICIO:
            raise ValueError("El estado debe ser 'activo' o 'inactivo'")
        return value


class CatalogoServicioResponse(BaseModel):
    id_catalogo_servicio: int
    id_taller: int
    nombre: str
    descripcion: str | None
    categoria: str
    unidad_medida: str
    precio_estandar: float
    estado: str
    fecha_creacion: datetime

    class Config:
        from_attributes = True
