import logging
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.usuarios.usuario import User
from app.repositories.solicitudes_repository import (
    create_solicitud,
    get_solicitud_by_id_for_user,
    list_solicitudes_by_user,
    update_solicitud_ai_analysis,
)
from app.repositories.vehiculos_repository import get_vehiculo_by_id
from app.schemas.solicitudes.solicitud_schema import SolicitudCreate
from app.services.openai_solicitud_analysis_service import analyze_solicitud_with_openai


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOADS_ROOT = PROJECT_ROOT / "uploads" / "solicitudes"
logger = logging.getLogger("solicitudes")


def _solicitud_response(solicitud) -> dict:
    return {
        "id_solicitud": solicitud.id_solicitud,
        "id_vehiculo": solicitud.id_vehiculo,
        "descripcion": solicitud.descripcion,
        "latitud": solicitud.latitud,
        "direccion": solicitud.direccion,
        "longitud": solicitud.longitud,
        "fecha": solicitud.fecha,
        "prioridad": solicitud.prioridad,
        "observaciones": solicitud.observaciones,
        "audio": solicitud.audio,
        "imagenes": solicitud.imagenes,
        "ronda_actual": solicitud.ronda_actual,
        "estado": solicitud.estado,
        "recomendacion": solicitud.recomendacion,
    }


def _guardar_archivo(upload: UploadFile, carpeta: str, tipo: str) -> str:
    content_type = upload.content_type or ""
    if tipo == "imagen" and not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Las imagenes deben ser archivos de tipo imagen",
        )

    if tipo == "audio" and not content_type.startswith("audio/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El audio debe ser un archivo de tipo audio",
        )

    destino = UPLOADS_ROOT / carpeta
    destino.mkdir(parents=True, exist_ok=True)

    extension = Path(upload.filename or "").suffix.lower()
    nombre_archivo = f"{uuid4().hex}{extension}"
    ruta_archivo = destino / nombre_archivo

    with ruta_archivo.open("wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)

    return f"/uploads/solicitudes/{carpeta}/{nombre_archivo}"


def registrar_solicitud(
    db: Session,
    id_vehiculo: int,
    descripcion: str,
    latitud: float,
    direccion: str | None,
    longitud: float,
    audio: UploadFile | None,
    imagenes: list[UploadFile] | None,
):
    vehiculo = get_vehiculo_by_id(db, id_vehiculo)
    if not vehiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehiculo no encontrado",
        )

    ruta_audio = _guardar_archivo(audio, "audios", "audio") if audio else None
    rutas_imagenes = [
        _guardar_archivo(imagen, "images", "imagen")
        for imagen in imagenes or []
    ] or None

    solicitud_data = SolicitudCreate(
        id_vehiculo=id_vehiculo,
        descripcion=descripcion,
        latitud=latitud,
        direccion=direccion,
        longitud=longitud,
        audio=ruta_audio,
        imagenes=rutas_imagenes,
    )

    try:
        solicitud = create_solicitud(db, solicitud_data)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo crear la solicitud",
        )

    try:
        analisis_ia = analyze_solicitud_with_openai(
            descripcion=solicitud.descripcion,
            audio=solicitud.audio,
            imagenes=solicitud.imagenes,
        )
        if analisis_ia:
            solicitud = update_solicitud_ai_analysis(
                db=db,
                solicitud=solicitud,
                prioridad=analisis_ia.get("prioridad"),
                observaciones=analisis_ia.get("observaciones"),
                recomendacion=analisis_ia.get("recomendacion"),
            )
    except Exception:
        logger.exception("No se pudo analizar la solicitud con OpenAI id_solicitud=%s", solicitud.id_solicitud)

    return _solicitud_response(solicitud)


def obtener_solicitud_por_id(
    db: Session,
    id_solicitud: int,
    current_user: User,
):
    solicitud = get_solicitud_by_id_for_user(db, id_solicitud, current_user.id_usuario)
    if not solicitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada",
        )

    return _solicitud_response(solicitud)


def listar_mis_solicitudes(
    db: Session,
    current_user: User,
) -> list[dict]:
    solicitudes = list_solicitudes_by_user(db, current_user.id_usuario)
    return [_solicitud_response(solicitud) for solicitud in solicitudes]
