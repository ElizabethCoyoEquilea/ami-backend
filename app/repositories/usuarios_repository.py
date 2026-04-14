from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.usuarios.persona import Persona
from app.models.usuarios.cliente import Cliente
from app.models.usuarios.rol import Rol
from app.models.usuarios.usuario import User
from app.models.usuarios.usuario_rol import UsuarioRol
from app.schemas.usuarios.usuarios_schema import UserCreate


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_role_by_id(db: Session, rol_id: int) -> Rol | None:
    return db.query(Rol).filter(Rol.id_rol == rol_id).first()


def get_cliente_by_codigo(db: Session, codigo: str) -> Cliente | None:
    return db.query(Cliente).filter(Cliente.codigo == codigo).first()


def create_user(
    db: Session,
    user_data: UserCreate,
    hashed_password: str,
    activo: bool = False,
    codigo_verificacion_hash: str | None = None,
    codigo_verificacion_expira_en: datetime | None = None,
    codigo_verificacion_intentos: int = 0,
) -> User:
    try:
        persona = Persona(**user_data.persona.model_dump())
        db.add(persona)
        db.flush()  # Genera persona.id_persona antes de crear usuario

        usuario = User(
            email=user_data.email,
            contrasena=hashed_password,
            id_persona=persona.id_persona,
            activo=activo,
            codigo_verificacion_hash=codigo_verificacion_hash,
            codigo_verificacion_expira_en=codigo_verificacion_expira_en,
            codigo_verificacion_intentos=codigo_verificacion_intentos,
        )

        db.add(usuario)
        db.commit()
        db.refresh(usuario)
        return usuario
    except SQLAlchemyError:
        db.rollback()
        raise


def create_user_with_role(
    db: Session,
    user_data: UserCreate,
    hashed_password: str,
    rol_id: int,
    activo: bool = True,
    codigo_verificacion_hash: str | None = None,
    codigo_verificacion_expira_en: datetime | None = None,
    codigo_verificacion_intentos: int = 0,
    codigo_cliente: str | None = None,
) -> User:
    """Crea un usuario y le asigna un rol automaticamente."""
    try:
        persona = Persona(**user_data.persona.model_dump())
        db.add(persona)
        db.flush()  # Genera persona.id_persona antes de crear usuario

        usuario = User(
            email=user_data.email,
            contrasena=hashed_password,
            id_persona=persona.id_persona,
            activo=activo,
            codigo_verificacion_hash=codigo_verificacion_hash,
            codigo_verificacion_expira_en=codigo_verificacion_expira_en,
            codigo_verificacion_intentos=codigo_verificacion_intentos,
        )

        db.add(usuario)
        db.flush()  # Flush para obtener el id_usuario sin hacer commit

        # Crear la relacion usuario-rol
        usuario_rol = UsuarioRol(
            id_usuario=usuario.id_usuario,
            id_rol=rol_id,
            activo=True,
        )
        db.add(usuario_rol)

        if codigo_cliente:
            cliente = Cliente(
                id_usuario=usuario.id_usuario,
                codigo=codigo_cliente,
            )
            db.add(cliente)

        db.commit()
        db.refresh(usuario)
        return usuario
    except SQLAlchemyError:
        db.rollback()
        raise
