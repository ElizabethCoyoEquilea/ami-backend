import shutil
from calendar import monthrange
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.solicitudes.asignacion import Asignacion
from app.models.solicitudes.calificacion import Calificacion
from app.models.solicitudes.cotizacion import Cotizacion
from app.models.solicitudes.pago import Pago
from app.models.solicitudes.servicio import Servicio
from app.models.talleres.taller import Taller
from app.models.usuarios.proveedor_servicio import ProveedorServicio
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


def _rango_dia_local(fecha: datetime) -> tuple[datetime, datetime]:
    inicio = fecha.replace(hour=0, minute=0, second=0, microsecond=0)
    fin = inicio + timedelta(days=1)
    return inicio.replace(tzinfo=None), fin.replace(tzinfo=None)


def _mismo_dia_mes_anterior(fecha: datetime) -> datetime:
    year = fecha.year
    month = fecha.month - 1
    if month == 0:
        month = 12
        year -= 1

    day = min(fecha.day, monthrange(year, month)[1])
    return fecha.replace(year=year, month=month, day=day)


def _sumar_ingresos_taller_en_rango(
    db: Session,
    id_taller: int,
    inicio: datetime,
    fin: datetime,
) -> float:
    total = (
        db.query(func.coalesce(func.sum(Pago.monto), 0))
        .join(Servicio, Servicio.id_pago == Pago.id_pago)
        .join(Asignacion, Asignacion.id_asignacion == Servicio.id_asignacion)
        .filter(
            Asignacion.id_taller == id_taller,
            Servicio.estado == "pagado",
            Servicio.fecha_fin >= inicio,
            Servicio.fecha_fin < fin,
            Pago.estado.in_(("pagado", "completado")),
        )
        .scalar()
    )
    return float(total or 0)


def _conteo_servicios_por_mes(db: Session, id_taller: int, anio: int) -> dict:
    etiquetas = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    inicio_anio = datetime(anio, 1, 1)
    fin_anio = datetime(anio + 1, 1, 1)
    conteos = {mes: 0 for mes in range(1, 13)}

    rows = (
        db.query(
            func.extract("month", Servicio.fecha_fin).label("mes"),
            func.count(Servicio.id_servicio),
        )
        .join(Asignacion, Asignacion.id_asignacion == Servicio.id_asignacion)
        .filter(
            Asignacion.id_taller == id_taller,
            Servicio.fecha_fin >= inicio_anio,
            Servicio.fecha_fin < fin_anio,
            Servicio.estado == "pagado",
        )
        .group_by("mes")
        .all()
    )

    for mes, cantidad in rows:
        conteos[int(mes)] = int(cantidad or 0)

    meses = [
        {
            "mes": mes,
            "etiqueta": etiquetas[mes - 1],
            "cantidad": conteos[mes],
        }
        for mes in range(1, 13)
    ]
    return {
        "anio": anio,
        "total": sum(item["cantidad"] for item in meses),
        "meses": meses,
    }


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


def obtener_dashboard_taller_hoy(db: Session, id_taller: int, id_usuario: int) -> dict:
    taller = get_active_taller_by_id(db, id_taller)
    if not taller or taller.id_usuario != id_usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taller no encontrado",
        )

    ahora = datetime.now(LA_PAZ_TZ)
    inicio_hoy, fin_hoy = _rango_dia_local(ahora)
    inicio_semana, _ = _rango_dia_local(ahora - timedelta(days=ahora.weekday()))
    mismo_dia_mes_anterior = _mismo_dia_mes_anterior(ahora)
    inicio_mes_anterior, fin_mes_anterior = _rango_dia_local(mismo_dia_mes_anterior)

    total_proveedores = (
        db.query(func.count(ProveedorServicio.id_proveedor))
        .filter(ProveedorServicio.id_taller == id_taller)
        .scalar()
        or 0
    )
    proveedores_disponibles = (
        db.query(func.count(ProveedorServicio.id_proveedor))
        .filter(
            ProveedorServicio.id_taller == id_taller,
            ProveedorServicio.estado == "Disponible",
        )
        .scalar()
        or 0
    )

    ingresos_hoy = _sumar_ingresos_taller_en_rango(db, id_taller, inicio_hoy, fin_hoy)
    ingresos_mes_anterior = _sumar_ingresos_taller_en_rango(
        db,
        id_taller,
        inicio_mes_anterior,
        fin_mes_anterior,
    )
    variacion = None
    if ingresos_mes_anterior > 0:
        variacion = round(
            ((ingresos_hoy - ingresos_mes_anterior) / ingresos_mes_anterior) * 100,
            2,
        )

    servicios_finalizados_hoy = (
        db.query(func.count(Servicio.id_servicio))
        .join(Asignacion, Asignacion.id_asignacion == Servicio.id_asignacion)
        .filter(
            Asignacion.id_taller == id_taller,
            Servicio.fecha_fin >= inicio_hoy,
            Servicio.fecha_fin < fin_hoy,
            Servicio.estado == "pagado",
        )
        .scalar()
        or 0
    )
    servicios_finalizados_semana = (
        db.query(func.count(Servicio.id_servicio))
        .join(Asignacion, Asignacion.id_asignacion == Servicio.id_asignacion)
        .filter(
            Asignacion.id_taller == id_taller,
            Servicio.fecha_fin >= inicio_semana,
            Servicio.fecha_fin < fin_hoy,
            Servicio.estado == "pagado",
        )
        .scalar()
        or 0
    )

    solicitudes_pendientes_cotizar = (
        db.query(func.count(Cotizacion.id_cotizacion))
        .filter(
            Cotizacion.id_taller == id_taller,
            Cotizacion.estado == "pendiente",
        )
        .scalar()
        or 0
    )
    asignaciones_pendientes_designar = (
        db.query(func.count(Asignacion.id_asignacion))
        .filter(
            Asignacion.id_taller == id_taller,
            Asignacion.id_proveedor.is_(None),
            Asignacion.estado.in_(
                (
                    "pendiente",
                    "Pendiente de asignar personal",
                )
            ),
        )
        .scalar()
        or 0
    )
    servicios_en_curso = (
        db.query(func.count(Servicio.id_servicio))
        .join(Asignacion, Asignacion.id_asignacion == Servicio.id_asignacion)
        .filter(
            Asignacion.id_taller == id_taller,
            Servicio.estado == "En curso",
        )
        .scalar()
        or 0
    )

    calificacion_data = (
        db.query(
            func.coalesce(func.avg(Calificacion.puntuacion), 0),
            func.count(Calificacion.id_calificacion),
        )
        .join(Servicio, Servicio.id_servicio == Calificacion.id_servicio)
        .join(Asignacion, Asignacion.id_asignacion == Servicio.id_asignacion)
        .filter(Asignacion.id_taller == id_taller)
        .first()
    )

    return {
        "id_taller": id_taller,
        "fecha": ahora.date().isoformat(),
        "generado_en": ahora,
        "total_proveedores": int(total_proveedores),
        "proveedores_disponibles": int(proveedores_disponibles),
        "ingresos_hoy": ingresos_hoy,
        "ingresos_mes_anterior_mismo_dia": ingresos_mes_anterior,
        "variacion_ingresos_vs_mes_anterior": variacion,
        "servicios_finalizados_hoy": int(servicios_finalizados_hoy),
        "servicios_finalizados_semana": int(servicios_finalizados_semana),
        "calificacion_promedio": round(float(calificacion_data[0] or 0), 1),
        "total_resenas": int(calificacion_data[1] or 0),
        "operaciones": {
            "solicitudes_pendientes_cotizar": int(solicitudes_pendientes_cotizar),
            "asignaciones_pendientes_designar": int(asignaciones_pendientes_designar),
            "servicios_en_curso": int(servicios_en_curso),
        },
        "servicios_por_mes": _conteo_servicios_por_mes(db, id_taller, ahora.year),
    }


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
