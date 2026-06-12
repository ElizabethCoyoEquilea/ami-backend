from sqlalchemy.orm import Session

from app.models.talleres.especialidad import Especialidad

DEFAULT_ESPECIALIDADES = [
    {
        "codigo": "MECANICA_GENERAL",
        "nombre": "Mecanica general",
        "descripcion": "Mecanica general",
    },
    {
        "codigo": "ELECTRICIDAD",
        "nombre": "Electricidad automotriz",
        "descripcion": "Electricidad automotriz",
    },
    {
        "codigo": "NEUMATICOS",
        "nombre": "Neumaticos y llantas",
        "descripcion": "Neumaticos y llantas",
    },
    {
        "codigo": "FRENOS",
        "nombre": "Sistema de frenos",
        "descripcion": "Sistema de frenos",
    },
    {
        "codigo": "MOTOR",
        "nombre": "Motor",
        "descripcion": "Motor",
    },
    {
        "codigo": "REFRIGERACION",
        "nombre": "Refrigeracion del motor",
        "descripcion": "Refrigeracion del motor",
    },
    {
        "codigo": "SUSPENSION_DIRECCION",
        "nombre": "Suspension y direccion",
        "descripcion": "Suspension y direccion",
    },
    {
        "codigo": "TRANSMISION",
        "nombre": "Transmision y embrague",
        "descripcion": "Transmision y embrague",
    },
    {
        "codigo": "MANTENIMIENTO",
        "nombre": "Mantenimiento preventivo",
        "descripcion": "Mantenimiento preventivo",
    },
    {
        "codigo": "AIRE_ACONDICIONADO",
        "nombre": "Aire acondicionado",
        "descripcion": "Aire acondicionado",
    },
    {
        "codigo": "DIAGNOSTICO",
        "nombre": "Diagnostico automotriz",
        "descripcion": "Diagnostico automotriz",
    },
    {
        "codigo": "REMOLQUE",
        "nombre": "Grua y traslado",
        "descripcion": "Grua y traslado",
    },
]


def seed_especialidades(db: Session) -> None:
    for especialidad_data in DEFAULT_ESPECIALIDADES:
        existe = (
            db.query(Especialidad)
            .filter(Especialidad.codigo == especialidad_data["codigo"])
            .first()
        )
        if not existe:
            db.add(Especialidad(**especialidad_data))
