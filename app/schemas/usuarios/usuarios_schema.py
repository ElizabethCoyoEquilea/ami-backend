from datetime import date
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
