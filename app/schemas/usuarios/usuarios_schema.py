from datetime import date, time
from pydantic import BaseModel, EmailStr, Field


# ==============================
# SCHEMAS PERSONA
# ==============================

class PersonaBase(BaseModel):
    nombre_completo: str = Field(min_length=1, max_length=150)
    fecha_nacimiento: date | None = None
    genero: str | None = Field(default=None, max_length=1)
    telefono: str | None = Field(default=None, max_length=20)
    documento: str | None = Field(default=None, max_length=50)


class PersonaCreate(PersonaBase):
    pass


class PersonaResponse(PersonaBase):
    id_persona: int

    class Config:
        from_attributes = True


# ==============================
# SCHEMAS USUARIO
# ==============================

class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    contrasena: str = Field(min_length=6, max_length=255)
    persona: PersonaCreate


class UserResponse(UserBase):
    id_usuario: int
    activo: bool
    persona: PersonaResponse

    class Config:
        from_attributes = True


# ==============================
# SCHEMAS AUTENTICACION
# ==============================

class LoginSchema(BaseModel):
    email: EmailStr
    contrasena: str = Field(min_length=6, max_length=255)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: int
    email: str


class ResendVerificationSchema(BaseModel):
    email: EmailStr


class VerifyUserSchema(BaseModel):
    email: EmailStr
    codigo: str = Field(min_length=4, max_length=12)


class ResetPasswordSchema(BaseModel):
    email: EmailStr


class MessageResponse(BaseModel):
    message: str


class ResultMessageResponse(BaseModel):
    result: bool
    message: str


class RegistrationResponse(BaseModel):
    registered: bool


class CreateClientResponse(BaseModel):
    result: bool
    message: str
    id_usuario: int
    id_rol: int
    id_cliente: int
    codigo_cliente: str


class ClientAssignmentResponse(BaseModel):
    is_client: bool
    id_usuario: int
    id_cliente: int | None = None
    codigo_cliente: str | None = None


class CurrentProviderUserResponse(BaseModel):
    id_usuario: int
    email: EmailStr
    activo: bool
    persona: PersonaResponse

    class Config:
        from_attributes = True


class CurrentProviderEmpresaResponse(BaseModel):
    id_taller: int
    id_usuario: int
    nombre: str
    descripcion: str | None = None
    radio_cobertura: float
    calificacion: float
    direccion: str
    longitud: float | None = None
    latitud: float | None = None
    horario_inicio: time
    horario_fin: time
    estado: str
    activo: bool

    class Config:
        from_attributes = True


class CurrentProviderServicioResponse(BaseModel):
    id_proveedor: int
    id_usuario: int
    id_taller: int
    estado: str | None = None
    especialidad: str | None = None

    class Config:
        from_attributes = True


class CurrentProviderEmpresaItemResponse(BaseModel):
    empresa: CurrentProviderEmpresaResponse
    proveedor_servicio: CurrentProviderServicioResponse


class CurrentProviderProfileResponse(BaseModel):
    usuario: CurrentProviderUserResponse
    empresas: list[CurrentProviderEmpresaItemResponse]


class TallerInvitationCreateSchema(BaseModel):
    email: EmailStr
    id_taller: int = Field(gt=0)


class TallerInvitationCreateResponse(BaseModel):
    result: bool
    message: str
    invitation_link: str


class TallerInvitationAcceptResponse(BaseModel):
    result: bool
    message: str
    id_usuario: int
    id_taller: int
    id_rol: int
