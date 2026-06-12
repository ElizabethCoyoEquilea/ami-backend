from sqlalchemy.orm import Session

from app.models.solicitudes.solicitud import Solicitud
from app.models.solicitudes.zona import Zona
from app.services.zonas_service import obtener_zona_por_coordenadas


ZONAS_SANTA_CRUZ = [
    {
        "nombre": "Centro",
        "descripcion": "Zona central de Santa Cruz de la Sierra.",
        "latitud_centro": -17.7833,
        "longitud_centro": -63.1821,
        "radio_aproximado": 5.0,
    },
    {
        "nombre": "Norte",
        "descripcion": "Zona norte de Santa Cruz de la Sierra.",
        "latitud_centro": -17.7200,
        "longitud_centro": -63.1800,
        "radio_aproximado": 8.0,
    },
    {
        "nombre": "Sur",
        "descripcion": "Zona sur de Santa Cruz de la Sierra.",
        "latitud_centro": -17.8600,
        "longitud_centro": -63.1800,
        "radio_aproximado": 8.0,
    },
    {
        "nombre": "Este",
        "descripcion": "Zona este de Santa Cruz de la Sierra.",
        "latitud_centro": -17.7800,
        "longitud_centro": -63.1000,
        "radio_aproximado": 8.0,
    },
    {
        "nombre": "Oeste",
        "descripcion": "Zona oeste de Santa Cruz de la Sierra.",
        "latitud_centro": -17.7800,
        "longitud_centro": -63.2600,
        "radio_aproximado": 8.0,
    },
]


def seed_zonas(db: Session) -> None:
    for zona_data in ZONAS_SANTA_CRUZ:
        zona = db.query(Zona).filter(Zona.nombre == zona_data["nombre"]).first()
        if zona:
            for field, value in zona_data.items():
                setattr(zona, field, value)
            continue

        db.add(Zona(**zona_data))

    db.flush()

    solicitudes_sin_zona = (
        db.query(Solicitud)
        .filter(Solicitud.id_zona.is_(None))
        .all()
    )
    for solicitud in solicitudes_sin_zona:
        zona = obtener_zona_por_coordenadas(
            db,
            solicitud.latitud,
            solicitud.longitud,
        )
        if zona:
            solicitud.id_zona = zona.id_zona
