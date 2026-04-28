from datetime import datetime, time

from pydantic import BaseModel, Field, field_validator, model_validator


MAX_RADIO_COBERTURA_KM = 100
ESTADOS_TALLER = {"abierto", "cerrado"}


class TallerBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str | None = Field(default=None, max_length=500)
    radio_cobertura: float = Field(ge=0, le=MAX_RADIO_COBERTURA_KM)
    calificacion: float = Field(default=0, ge=0, le=5)
    direccion: str = Field(min_length=1, max_length=255)
    longitud: float | None = None
    latitud: float | None = None
    qr: str | None = Field(default=None, max_length=1000)
    horario_inicio: time
    horario_fin: time
    estado: str | None = None
    activo: bool = True

    @field_validator("nombre", "direccion")
    @classmethod
    def validar_texto_obligatorio(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Este campo es obligatorio")
        return value

    @field_validator("descripcion", "qr")
    @classmethod
    def limpiar_texto_opcional(cls, value: str | None) -> str | None:
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
        if value not in ESTADOS_TALLER:
            raise ValueError("El estado debe ser 'abierto' o 'cerrado'")
        return value

    @model_validator(mode="after")
    def validar_horarios(self):
        if self.horario_inicio >= self.horario_fin:
            raise ValueError("horario_inicio debe ser menor que horario_fin")
        return self


class TallerCreate(TallerBase):
    estado: str | None = None
    activo: bool = True


class TallerUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=150)
    descripcion: str | None = Field(default=None, max_length=500)
    radio_cobertura: float | None = Field(default=None, ge=0, le=MAX_RADIO_COBERTURA_KM)
    calificacion: float | None = Field(default=None, ge=0, le=5)
    direccion: str | None = Field(default=None, min_length=1, max_length=255)
    longitud: float | None = None
    latitud: float | None = None
    qr: str | None = Field(default=None, max_length=1000)
    horario_inicio: time | None = None
    horario_fin: time | None = None
    estado: str | None = None
    activo: bool | None = None

    @field_validator("nombre", "direccion")
    @classmethod
    def validar_texto_si_llega(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("Este campo no puede estar vacio")
        return value

    @field_validator("descripcion", "qr")
    @classmethod
    def limpiar_texto_opcional(cls, value: str | None) -> str | None:
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
        if value not in ESTADOS_TALLER:
            raise ValueError("El estado debe ser 'abierto' o 'cerrado'")
        return value

    @model_validator(mode="after")
    def validar_horarios_si_llegan(self):
        if (
            self.horario_inicio is not None
            and self.horario_fin is not None
            and self.horario_inicio >= self.horario_fin
        ):
            raise ValueError("horario_inicio debe ser menor que horario_fin")
        return self


class TallerResponse(BaseModel):
    id_taller: int
    id_usuario: int
    nombre: str
    descripcion: str | None
    radio_cobertura: float
    calificacion: float
    direccion: str
    longitud: float | None
    latitud: float | None
    qr: str | None
    horario_inicio: time
    horario_fin: time
    estado: str
    activo: bool

    class Config:
        from_attributes = True


# ==============================
# SCHEMAS PROVEEDOR SERVICIO
# ==============================

class PersonaBasicResponse(BaseModel):
    id_persona: int
    nombre_completo: str
    telefono: str | None
    documento: str | None

    class Config:
        from_attributes = True


class UsuarioBasicResponse(BaseModel):
    id_usuario: int
    email: str
    persona: PersonaBasicResponse

    class Config:
        from_attributes = True


class ProveedorServicioResponse(BaseModel):
    id_proveedor: int
    id_usuario: int
    id_taller: int
    estado: str | None
    especialidad: str | None
    usuario: UsuarioBasicResponse

    class Config:
        from_attributes = True


class ListarProveedoresResponse(BaseModel):
    id_taller: int
    total_proveedores: int
    proveedores: list[ProveedorServicioResponse]


class TallerDashboardHoyResponse(BaseModel):
    id_taller: int
    fecha: str
    generado_en: datetime
    total_proveedores: int
    proveedores_disponibles: int
    ingresos_hoy: float
    ingresos_mes_anterior_mismo_dia: float
    variacion_ingresos_vs_mes_anterior: float | None
    servicios_finalizados_hoy: int
    servicios_finalizados_semana: int
    calificacion_promedio: float
    total_resenas: int
    operaciones: dict
    servicios_por_mes: dict
