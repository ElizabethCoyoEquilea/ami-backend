from pydantic import BaseModel, Field, field_validator


class EspecialidadBase(BaseModel):
    codigo: str = Field(min_length=1, max_length=50)
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str | None = Field(default=None, max_length=500)

    @field_validator("codigo", "nombre")
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


class EspecialidadCreate(EspecialidadBase):
    pass


class EspecialidadUpdate(BaseModel):
    codigo: str | None = Field(default=None, min_length=1, max_length=50)
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    descripcion: str | None = Field(default=None, max_length=500)

    @field_validator("codigo", "nombre")
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


class EspecialidadResponse(BaseModel):
    id_especialidad: int
    codigo: str
    nombre: str
    descripcion: str | None

    class Config:
        from_attributes = True
