from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.solicitudes.pago_schema import PagoResponse


class CatalogoServicioResumenResponse(BaseModel):
    id_catalogo_servicio: int
    nombre: str
    categoria: str
    unidad_medida: str

    class Config:
        from_attributes = True


class DetalleServicioBase(BaseModel):
    id_catalogo_servicio: int = Field(gt=0)
    cantidad: int = Field(gt=0)
    precio: float = Field(ge=0)
    nombre: str = Field(min_length=1, max_length=150)
    observacion: str | None = Field(default=None, max_length=500)

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El nombre es obligatorio")
        return value

    @field_validator("observacion")
    @classmethod
    def limpiar_observacion(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        return value or None


class DetalleServicioCreate(DetalleServicioBase):
    pass


class DetalleServicioResponse(DetalleServicioBase):
    id_detalle_servicio: int
    id_servicio: int
    sub_total: float
    catalogo_servicio: CatalogoServicioResumenResponse | None = None

    class Config:
        from_attributes = True


class ServicioCreate(BaseModel):
    id_asignacion: int = Field(gt=0)
    total: float | None = Field(default=None, ge=0)
    fecha_inicio: datetime | None = None
    fecha_fin: datetime | None = None
    estado: str | None = "pendiente"
    detalles: list[DetalleServicioCreate] = Field(default_factory=list)

    @field_validator("estado")
    @classmethod
    def validar_estado(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("El estado no puede estar vacio")
        return value


class ServicioResponse(BaseModel):
    id_servicio: int
    id_asignacion: int
    id_pago: int | None = None
    id_usuario_cliente: int | None = None
    total: float
    fecha_inicio: datetime | None
    fecha_fin: datetime | None
    estado: str
    detalles_servicio: list[DetalleServicioResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class ServicioResumenResponse(BaseModel):
    id_servicio: int
    id_asignacion: int
    id_pago: int | None = None
    total: float
    fecha_inicio: datetime | None
    fecha_fin: datetime | None
    estado: str

    class Config:
        from_attributes = True


class ServicioFacturaResponse(BaseModel):
    servicio: ServicioResponse
    detalles: list[DetalleServicioResponse] = Field(default_factory=list)
    pago: PagoResponse | None = None
    total: float
