from pydantic import BaseModel, Field

from app.schemas.talleres.especialidad_schema import EspecialidadResponse


class ProveedorEspecialidadBase(BaseModel):
    id_proveedor: int = Field(gt=0)
    id_especialidad: int = Field(gt=0)
    activo: bool = True


class ProveedorEspecialidadCreate(ProveedorEspecialidadBase):
    pass


class ProveedorEspecialidadUpdate(BaseModel):
    id_especialidad: int | None = Field(default=None, gt=0)
    activo: bool | None = None


class ProveedorEspecialidadResponse(BaseModel):
    id_proveedor_especialidad: int
    id_proveedor: int
    id_especialidad: int
    activo: bool
    especialidad: EspecialidadResponse | None = None

    class Config:
        from_attributes = True
