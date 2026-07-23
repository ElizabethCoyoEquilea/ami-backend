from datetime import datetime
import re
import unicodedata
from math import asin, cos, radians, sin, sqrt

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.solicitudes.asignacion import Asignacion
from app.models.talleres.catalogo_servicio import CatalogoServicio
from app.models.talleres.taller import Taller
from app.models.usuarios.proveedor_especialidad import ProveedorEspecialidad
from app.models.usuarios.proveedor_servicio import ProveedorServicio


EARTH_RADIUS_KM = 6371
AVERAGE_URBAN_SPEED_KMH = 35
DISTANCE_WEIGHT = 0.35
COMPATIBILITY_WEIGHT = 0.25
AVAILABILITY_WEIGHT = 0.15
ETA_WEIGHT = 0.10
ASSIGNMENTS_WEIGHT = 0.10
RATING_WEIGHT = 0.05
MAX_AVAILABILITY_PROVIDERS = 3
MAX_RESPONSE_TIME_MINUTES = 60


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text or "")
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn").lower()


def _tokenize_text(text: str) -> list[str]:
    return re.findall(r"\b[a-z0-9]+\b", _normalize_text(text))


def _phrase_tokens(text: str) -> tuple[str, ...]:
    return tuple(_tokenize_text(text))


def _matches_phrase(description: str, phrase_tokens: tuple[str, ...]) -> bool:
    if not phrase_tokens:
        return False

    description_tokens = set(_tokenize_text(description))
    return set(phrase_tokens).issubset(description_tokens)


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


def _build_specialty_terms(workshop: Taller) -> list[tuple[str, ...]]:
    terms: list[tuple[str, ...]] = []

    for catalogo in workshop.catalogo_servicios:
        if catalogo.nombre:
            terms.append(_phrase_tokens(catalogo.nombre))
        if catalogo.descripcion:
            terms.append(_phrase_tokens(catalogo.descripcion))
        if catalogo.especialidad and catalogo.especialidad.nombre:
            terms.append(_phrase_tokens(catalogo.especialidad.nombre))

    for proveedor in workshop.proveedores_servicio:
        for proveedor_especialidad in proveedor.proveedor_especialidades:
            especialidad = proveedor_especialidad.especialidad
            if especialidad and especialidad.nombre:
                terms.append(_phrase_tokens(especialidad.nombre))

    return [term for term in terms if term]


def _compute_compatibility_score(description: str, terms: list[tuple[str, ...]]) -> float:
    if not terms:
        return 0.0

    matches = sum(1 for term in terms if _matches_phrase(description, term))
    return min(matches / len(terms), 1.0)


def recommend_workshops(
    db: Session,
    client_lat: float,
    client_lng: float,
    descripcion: str | None = None,
    exclude_taller_ids: set[int] | None = None,
    top_n: int = 3,
) -> list[dict]:
    descripcion = descripcion or ""
    exclude_taller_ids = exclude_taller_ids or set()

    available_providers = (
        db.query(
            ProveedorServicio.id_taller,
            func.count(ProveedorServicio.id_proveedor).label("total"),
        )
        .filter(func.coalesce(func.lower(ProveedorServicio.estado), "disponible").in_(["disponible", "activo", "online"]))
        .group_by(ProveedorServicio.id_taller)
        .subquery()
    )

    assignments = (
        db.query(
            Asignacion.id_taller,
            func.count(Asignacion.id_asignacion).label("total_asignaciones"),
        )
        .group_by(Asignacion.id_taller)
        .subquery()
    )

    query = (
        db.query(
            Taller,
            func.coalesce(available_providers.c.total, 0).label("proveedores_disponibles"),
            func.coalesce(assignments.c.total_asignaciones, 0).label("total_asignaciones"),
        )
        .outerjoin(available_providers, available_providers.c.id_taller == Taller.id_taller)
        .outerjoin(assignments, assignments.c.id_taller == Taller.id_taller)
        .filter(
            Taller.activo.is_(True),
            Taller.estado == "abierto",
            Taller.latitud.is_not(None),
            Taller.longitud.is_not(None),
        )
    )

    if exclude_taller_ids:
        query = query.filter(Taller.id_taller.notin_(exclude_taller_ids))

    workshops = (
        query
        .options(
            joinedload(Taller.catalogo_servicios).joinedload(CatalogoServicio.especialidad),
            joinedload(Taller.proveedores_servicio)
            .joinedload(ProveedorServicio.proveedor_especialidades)
            .joinedload(ProveedorEspecialidad.especialidad),
        )
        .all()
    )

    recommendations: list[dict] = []
    max_assignments = max(
        (int(total_asignaciones or 0) for _, _, total_asignaciones in workshops),
        default=0,
    )
    max_assignments = max(max_assignments, 1)

    for workshop, available_provider_count, total_asignaciones in workshops:
        available_provider_count = int(available_provider_count or 0)
        if available_provider_count <= 0:
            continue

        distance_km = _haversine_distance_km(
            client_lat,
            client_lng,
            workshop.latitud,
            workshop.longitud,
        )
        coverage_radius_km = float(workshop.radio_cobertura or 0)
        if coverage_radius_km <= 0 or distance_km > coverage_radius_km:
            continue

        specialty_terms = _build_specialty_terms(workshop)
        compatibility_score = _compute_compatibility_score(descripcion, specialty_terms)
        distance_score = 1 - (distance_km / coverage_radius_km)
        availability_score = min(available_provider_count / MAX_AVAILABILITY_PROVIDERS, 1.0)
        eta_score = 1 - min((workshop.tiempo_respuesta or (MAX_RESPONSE_TIME_MINUTES / 2)) / MAX_RESPONSE_TIME_MINUTES, 1.0)
        assignment_score = min(int(total_asignaciones or 0) / max_assignments, 1.0)
        rating_score = min(max(float(workshop.calificacion or 0) / 5, 0), 1)

        score = (
            distance_score * DISTANCE_WEIGHT
            + compatibility_score * COMPATIBILITY_WEIGHT
            + availability_score * AVAILABILITY_WEIGHT
            + eta_score * ETA_WEIGHT
            + assignment_score * ASSIGNMENTS_WEIGHT
            + rating_score * RATING_WEIGHT
        ) * 100

        recommendations.append(
            {
                "id_taller": workshop.id_taller,
                "nombre": workshop.nombre,
                "distancia_km": round(distance_km, 2),
                "calificacion": float(workshop.calificacion or 0),
                "score": round(score, 2),
                "motivo_recomendacion": (
                    f"Cercania {round(distance_km, 2)} km, cobertura {round(coverage_radius_km, 2)} km, "
                    f"compatibilidad {round(compatibility_score * 100)}%, "
                    f"proveedores disponibles {available_provider_count}, "
                    f"tiempo de respuesta {workshop.tiempo_respuesta or 0} min, "
                    f"asignaciones {int(total_asignaciones or 0)}, "
                    f"calificacion {round(float(workshop.calificacion or 0), 1)}/5."
                ),
            }
        )

    sorted_recommendations = sorted(
        recommendations,
        key=lambda item: (item["score"], -item["distancia_km"]),
        reverse=True,
    )

    return sorted_recommendations[:top_n]
