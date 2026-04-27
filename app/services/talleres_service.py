import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.solicitudes.cotizacion import Cotizacion
from app.models.talleres.taller import Taller
from app.repositories.talleres_repository import (
    create_taller,
    get_active_taller_by_id,
    get_taller_by_id,
    list_active_talleres,
    list_talleres_by_usuario,
    logical_delete_taller,
    update_taller,
    get_proveedores_by_taller,
    list_asignaciones_by_taller,
)
from app.schemas.talleres.taller_schema import TallerCreate, TallerUpdate


try:
    LA_PAZ_TZ = ZoneInfo("America/La_Paz")
except ZoneInfoNotFoundError:
    LA_PAZ_TZ = timezone(timedelta(hours=-4))


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOADS_ROOT = PROJECT_ROOT / "uploads" / "talleres" / "qr"


def _guardar_qr(upload: UploadFile) -> str:
    content_type = upload.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El QR debe ser un archivo de tipo imagen",
        )

    UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
    extension = Path(upload.filename or "").suffix.lower()
    nombre_archivo = f"{uuid4().hex}{extension}"
    ruta_archivo = UPLOADS_ROOT / nombre_archivo

    with ruta_archivo.open("wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)

    return f"/uploads/talleres/qr/{nombre_archivo}"


def _calcular_estado(taller: Taller) -> str:
    hora_actual = datetime.now(LA_PAZ_TZ).time()
    if taller.horario_inicio <= hora_actual <= taller.horario_fin:
        return "abierto"
    return "cerrado"


def _actualizar_estado_por_horario(db: Session, taller: Taller) -> Taller:
    estado_actual = _calcular_estado(taller)
    if taller.estado != estado_actual:
        taller.estado = estado_actual
        db.commit()
        db.refresh(taller)
    return taller


def _validar_horario_completo(taller: Taller, taller_data: TallerUpdate) -> None:
    horario_inicio = taller_data.horario_inicio or taller.horario_inicio
    horario_fin = taller_data.horario_fin or taller.horario_fin

    if horario_inicio >= horario_fin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="horario_inicio debe ser menor que horario_fin",
        )


def registrar_taller(
    db: Session,
    taller_data: TallerCreate,
    id_usuario: int,
    qr: UploadFile | None = None,
) -> Taller:
    try:
        taller_data.estado = taller_data.estado or "cerrado"
        taller_data.activo = True
        if qr:
            taller_data.qr = _guardar_qr(qr)
        taller = create_taller(db, taller_data, id_usuario)
        return _actualizar_estado_por_horario(db, taller)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo crear el taller",
        )


def listar_talleres(db: Session) -> list[Taller]:
    talleres = list_active_talleres(db)
    for taller in talleres:
        _actualizar_estado_por_horario(db, taller)
    return talleres


def listar_talleres_por_usuario(db: Session, id_usuario: int) -> list[Taller]:
    talleres = list_talleres_by_usuario(db, id_usuario)
    for taller in talleres:
        _actualizar_estado_por_horario(db, taller)
    return talleres


def obtener_taller(db: Session, id_taller: int) -> Taller:
    taller = get_active_taller_by_id(db, id_taller)
    if not taller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taller no encontrado",
        )
    return _actualizar_estado_por_horario(db, taller)


def modificar_taller(
    db: Session,
    id_taller: int,
    taller_data: TallerUpdate,
    id_usuario: int,
    qr: UploadFile | None = None,
) -> Taller:
    taller = get_taller_by_id(db, id_taller)
    if not taller or taller.id_usuario != id_usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taller no encontrado",
        )

    _validar_horario_completo(taller, taller_data)

    try:
        if qr:
            taller_data.qr = _guardar_qr(qr)
        taller_actualizado = update_taller(db, taller, taller_data)
        return _actualizar_estado_por_horario(db, taller_actualizado)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo actualizar el taller",
        )


def eliminar_taller(db: Session, id_taller: int) -> dict[str, str]:
    taller = get_active_taller_by_id(db, id_taller)
    if not taller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taller no encontrado",
        )

    try:
        logical_delete_taller(db, taller)
        return {"message": "Taller eliminado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo eliminar el taller",
        )


def listar_proveedores_taller(db: Session, id_taller: int, id_usuario: int) -> dict:
    taller = get_active_taller_by_id(db, id_taller)
    if not taller or taller.id_usuario != id_usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taller no encontrado",
        )

    proveedores = get_proveedores_by_taller(db, id_taller)
    return {
        "id_taller": id_taller,
        "total_proveedores": len(proveedores),
        "proveedores": proveedores,
    }


def listar_asignaciones_taller(db: Session, id_taller: int):
    taller = get_active_taller_by_id(db, id_taller)
    if not taller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taller no encontrado",
        )

    asignaciones = list_asignaciones_by_taller(db, id_taller)
    solicitud_ids = [asignacion.id_solicitud for asignacion in asignaciones]

    cotizaciones_por_solicitud = {}
    if solicitud_ids:
        cotizaciones = (
            db.query(Cotizacion)
            .filter(
                Cotizacion.id_taller == id_taller,
                Cotizacion.id_solicitud.in_(solicitud_ids),
            )
            .all()
        )
        cotizaciones_por_solicitud = {
            cotizacion.id_solicitud: cotizacion.id_cotizacion
            for cotizacion in cotizaciones
        }

    return [
        {
            "id_asignacion": asignacion.id_asignacion,
            "id_cotizacion": cotizaciones_por_solicitud.get(asignacion.id_solicitud),
            "id_solicitud": asignacion.id_solicitud,
            "id_taller": asignacion.id_taller,
            "id_proveedor": asignacion.id_proveedor,
            "fecha": asignacion.fecha,
            "estado": asignacion.estado,
            "solicitud": asignacion.solicitud,
            "servicios": asignacion.servicios,
        }
        for asignacion in asignaciones
    ]
