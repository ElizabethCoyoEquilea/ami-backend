from math import asin, cos, radians, sin, sqrt

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.talleres.taller import Taller
from app.models.usuarios.proveedor_servicio import ProveedorServicio


EARTH_RADIUS_KM = 6371
AVERAGE_URBAN_SPEED_KMH = 35
DISTANCE_WEIGHT = 0.35
RATING_WEIGHT = 0.25
AVAILABILITY_WEIGHT = 0.15
ETA_WEIGHT = 0.25


def _haversine_distance_km(
    origin_lat: float,
    origin_lng: float,
    destination_lat: float,
    destination_lng: float,
) -> float:
    lat_delta = radians(destination_lat - origin_lat)
    lng_delta = radians(destination_lng - origin_lng)
    origin_lat_rad = radians(origin_lat)
    destination_lat_rad = radians(destination_lat)

    a = (
        sin(lat_delta / 2) ** 2
        + cos(origin_lat_rad)
        * cos(destination_lat_rad)
        * sin(lng_delta / 2) ** 2
    )
    c = 2 * asin(sqrt(a))
    return EARTH_RADIUS_KM * c


def _estimated_arrival_minutes(distance_km: float) -> float:
    return (distance_km / AVERAGE_URBAN_SPEED_KMH) * 60


def recommend_workshops(
    db: Session,
    client_lat: float,
    client_lng: float,
) -> list[dict]:
    available_providers = (
        db.query(
            ProveedorServicio.id_taller,
            func.count(ProveedorServicio.id_proveedor).label("total"),
        )
        .filter(func.lower(ProveedorServicio.estado) == "disponible")
        .group_by(ProveedorServicio.id_taller)
        .subquery()
    )

    workshops = (
        db.query(Taller, func.coalesce(available_providers.c.total, 0).label("proveedores_disponibles"))
        .outerjoin(available_providers, available_providers.c.id_taller == Taller.id_taller)
        .filter(
            Taller.activo.is_(True),
            Taller.estado == "abierto",
            Taller.latitud.is_not(None),
            Taller.longitud.is_not(None),
        )
        .all()
    )

    recommendations = []
    for workshop, available_provider_count in workshops:
        if int(available_provider_count or 0) <= 0:
            continue

        distance_km = _haversine_distance_km(
            client_lat,
            client_lng,
            workshop.latitud,
            workshop.longitud,
        )
        coverage_radius_km = float(workshop.radio_cobertura or 0)
        if distance_km > coverage_radius_km:
            continue

        estimated_arrival_minutes = _estimated_arrival_minutes(distance_km)
        max_arrival_minutes = _estimated_arrival_minutes(coverage_radius_km)
        distance_score = 1 - (distance_km / coverage_radius_km) if coverage_radius_km > 0 else 1
        rating_score = min(max(float(workshop.calificacion or 0) / 5, 0), 1)
        availability_score = 1
        eta_score = (
            1 - (estimated_arrival_minutes / max_arrival_minutes)
            if max_arrival_minutes > 0
            else 1
        )
        score = (
            distance_score * DISTANCE_WEIGHT
            + rating_score * RATING_WEIGHT
            + availability_score * AVAILABILITY_WEIGHT
            + eta_score * ETA_WEIGHT
        ) * 100

        recommendations.append(
            {
                "id_taller": workshop.id_taller,
                "nombre": workshop.nombre,
                "distancia_km": round(distance_km, 2),
                "calificacion": float(workshop.calificacion or 0),
                "score": round(score, 2),
                "motivo_recomendacion": (
                    f"Esta a {round(distance_km, 2)} km, dentro de su radio de "
                    f"{round(coverage_radius_km, 2)} km, con calificacion "
                    f"{round(float(workshop.calificacion or 0), 1)}/5, "
                    f"{int(available_provider_count)} proveedor(es) disponible(s) "
                    f"y llegada estimada de {round(estimated_arrival_minutes)} min."
                ),
            }
        )

    sorted_recommendations = sorted(
        recommendations,
        key=lambda item: (item["score"], -item["distancia_km"]),
        reverse=True,
    )

    if 2 <= len(sorted_recommendations) <= 3:
        return sorted_recommendations[:1]
    if len(sorted_recommendations) > 3:
        return sorted_recommendations[:2]
    return sorted_recommendations
