from datetime import date

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.usuarios.persona import Persona
from app.models.usuarios.usuario import User
from app.models.usuarios.usuario_rol import UsuarioRol


USUARIOS_INICIALES = [
    {
        "email": "ayrton.daza.1230@gmail.com",
        "contrasena": "123456",
        "persona": {
            "nombre_completo": "Ayrton Daza Miranda",
            "fecha_nacimiento": date(2002, 12, 10),
            "genero": "M",
            "telefono": "61524977",
            "documento": "12345678",
        },
    },
    {
        "email": "cee777578@gmail.com",
        "contrasena": "123456",
        "persona": {
            "nombre_completo": "Elizaabeth Coyo Equilea",
            "fecha_nacimiento": date(2001, 12, 31),
            "genero": "F",
            "telefono": "71687109",
            "documento": "12345678",
        },
    },
]


def seed_usuarios(db: Session) -> None:
    """
    Crea usuarios activos/verificados como si hubieran completado registro y verificacion.
    Tambien asigna rol administrador (id_rol=1).
    """
    for data in USUARIOS_INICIALES:
        email = data["email"]
        existente = db.query(User).filter(User.email == email).first()

        if not existente:
            persona = Persona(**data["persona"])
            db.add(persona)
            db.flush()

            usuario = User(
                email=email,
                contrasena=get_password_hash(data["contrasena"]),
                id_persona=persona.id_persona,
                activo=True,
                codigo_verificacion_hash=None,
                codigo_verificacion_expira_en=None,
                codigo_verificacion_intentos=0,
            )
            db.add(usuario)
            db.flush()
            user_id = usuario.id_usuario
        else:
            existente.activo = True
            existente.codigo_verificacion_hash = None
            existente.codigo_verificacion_expira_en = None
            existente.codigo_verificacion_intentos = 0
            user_id = existente.id_usuario

        rol_admin = (
            db.query(UsuarioRol)
            .filter(UsuarioRol.id_usuario == user_id, UsuarioRol.id_rol == 1)
            .first()
        )
        if not rol_admin:
            db.add(
                UsuarioRol(
                    id_usuario=user_id,
                    id_rol=1,
                    activo=True,
                )
            )
