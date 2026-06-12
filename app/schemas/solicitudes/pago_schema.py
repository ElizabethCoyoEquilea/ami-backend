from datetime import datetime
from decimal import Decimal

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


class PagoClienteVehiculoResponse(BaseModel):
    id_vehiculo: int
    marca: str
    modelo: str
    placa: str


class PagoClienteSolicitudResponse(BaseModel):
    id_solicitud: int
    descripcion: str
    fecha: datetime
    estado: str


class PagoClienteAsignacionResponse(BaseModel):
    id_asignacion: int
    id_taller: int
    id_proveedor: int | None
    fecha_inicio: datetime
    fecha_fin: datetime | None
    tiempo_llegada: Decimal | None
    estado: str


class PagoClienteDetalleServicioResponse(BaseModel):
    id_detalle_servicio: int
    id_catalogo_servicio: int
    nombre: str
    cantidad: int
    precio: float
    sub_total: float
    observacion: str | None


class PagoClienteServicioResponse(BaseModel):
    id_servicio: int
    total: float
    fecha_inicio: datetime | None
    fecha_fin: datetime | None
    estado: str
    detalles_servicio: list[PagoClienteDetalleServicioResponse]


class PagoClienteResponse(BaseModel):
    pago: PagoResponse
    servicio: PagoClienteServicioResponse
    asignacion: PagoClienteAsignacionResponse
    solicitud: PagoClienteSolicitudResponse
    vehiculo: PagoClienteVehiculoResponse
