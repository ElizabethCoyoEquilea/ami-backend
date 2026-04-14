from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.talleres.taller import Taller
from app.repositories.talleres_repository import (
    create_taller,
    get_active_taller_by_id,
    list_active_talleres,
    logical_delete_taller,
    update_taller,
)
from app.schemas.talleres.taller_schema import TallerCreate, TallerUpdate


try:
    LA_PAZ_TZ = ZoneInfo("America/La_Paz")
except ZoneInfoNotFoundError:
    LA_PAZ_TZ = timezone(timedelta(hours=-4))


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


def registrar_taller(db: Session, taller_data: TallerCreate) -> Taller:
    try:
        taller_data.estado = taller_data.estado or "cerrado"
        taller_data.activo = True
        taller = create_taller(db, taller_data)
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


def obtener_taller(db: Session, id_taller: int) -> Taller:
    taller = get_active_taller_by_id(db, id_taller)
    if not taller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taller no encontrado",
        )
    return _actualizar_estado_por_horario(db, taller)


def modificar_taller(db: Session, id_taller: int, taller_data: TallerUpdate) -> Taller:
    taller = get_active_taller_by_id(db, id_taller)
    if not taller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taller no encontrado",
        )

    _validar_horario_completo(taller, taller_data)

    try:
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
