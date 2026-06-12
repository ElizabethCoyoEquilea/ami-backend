from math import asin, cos, radians, sin, sqrt

from sqlalchemy.orm import Session

from app.models.solicitudes.zona import Zona


def _distancia_km(
    latitud_a: float,
    longitud_a: float,
    latitud_b: float,
    longitud_b: float,
) -> float:
    radio_tierra_km = 6371.0
    d_latitud = radians(latitud_b - latitud_a)
    d_longitud = radians(longitud_b - longitud_a)
    latitud_a_rad = radians(latitud_a)
    latitud_b_rad = radians(latitud_b)

    haversine = (
        sin(d_latitud / 2) ** 2
        + cos(latitud_a_rad) * cos(latitud_b_rad) * sin(d_longitud / 2) ** 2
    )
    return 2 * radio_tierra_km * asin(sqrt(haversine))


def obtener_zona_por_coordenadas(
    db: Session,
    latitud: float | None,
    longitud: float | None,
) -> Zona | None:
    if latitud is None or longitud is None:
        return None

    zonas = db.query(Zona).order_by(Zona.id_zona).all()
    if not zonas:
        return None

    zonas_con_distancia = [
        (
            zona,
            _distancia_km(
                latitud,
                longitud,
                zona.latitud_centro,
                zona.longitud_centro,
            ),
        )
        for zona in zonas
    ]
    zonas_dentro_radio = [
        item for item in zonas_con_distancia if item[1] <= item[0].radio_aproximado
    ]
    zona, _ = min(zonas_dentro_radio or zonas_con_distancia, key=lambda item: item[1])
    return zona
