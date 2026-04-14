from sqlalchemy.orm import Session

from app.models.usuarios.rol import Rol

DEFAULT_ROLES = [
    {
        "nombre": "ADMINISTRADOR",
        "descripcion": "ADMINISTRADOR",
        "activo": True,
    },
    {
        "nombre": "PROVEEDOR DE SERVICIO",
        "descripcion": "PROVEEDOR DE SERVICIO",
        "activo": True,
    },
    {
        "nombre": "CLIENTE",
        "descripcion": "CLIENTE",
        "activo": True,
    },
]


def seed_roles(db: Session) -> None:
    for role_data in DEFAULT_ROLES:
        existe = db.query(Rol).filter(Rol.nombre == role_data["nombre"]).first()
        if not existe:
            db.add(Rol(**role_data))
