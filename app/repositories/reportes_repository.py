from collections import defaultdict
from datetime import datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.solicitudes.asignacion import Asignacion
from app.models.solicitudes.detalle_servicio import DetalleServicio
from app.models.solicitudes.solicitud import Solicitud
from app.models.solicitudes.servicio import Servicio
from app.models.talleres.taller import Taller
from app.models.usuarios.cliente import Cliente
from app.models.usuarios.persona import Persona
from app.models.usuarios.proveedor_servicio import ProveedorServicio
from app.models.usuarios.usuario import User
from app.models.usuarios.vehiculo import Vehiculo
from app.schemas.reportes_schema import ReporteFilters


def _money(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _dt(value: Any) -> str | None:
    return value.isoformat() if value else None


def _date_bounds(filters: ReporteFilters) -> tuple[datetime | None, datetime | None]:
    start = datetime.combine(filters.date_from, time.min) if filters.date_from else None
    end = datetime.combine(filters.date_to, time.max) if filters.date_to else None
    return start, end


def _apply_common_filters(query, filters: ReporteFilters):
    start, end = _date_bounds(filters)
    if start:
        query = query.filter(Servicio.fecha_inicio >= start)
    if end:
        query = query.filter(Servicio.fecha_inicio <= end)
    if filters.status:
        query = query.filter(func.lower(Servicio.estado) == filters.status.lower())
    if filters.client_id:
        query = query.filter(Cliente.id_cliente == filters.client_id)
    if filters.vehicle_id:
        query = query.filter(Vehiculo.id_vehiculo == filters.vehicle_id)
    if filters.technician_id:
        query = query.filter(ProveedorServicio.id_proveedor == filters.technician_id)
    if filters.plate:
        query = query.filter(func.lower(Vehiculo.placa) == filters.plate.lower())
    return query


def _base_service_query(db: Session, id_taller: int):
    return (
        db.query(Servicio)
        .join(Asignacion, Asignacion.id_asignacion == Servicio.id_asignacion)
        .join(Solicitud, Solicitud.id_solicitud == Asignacion.id_solicitud)
        .join(Vehiculo, Vehiculo.id_vehiculo == Solicitud.id_vehiculo)
        .join(Cliente, Cliente.id_cliente == Vehiculo.id_cliente)
        .outerjoin(ProveedorServicio, ProveedorServicio.id_proveedor == Asignacion.id_proveedor)
        .options(
            joinedload(Servicio.detalles_servicio),
            joinedload(Servicio.asignacion)
            .joinedload(Asignacion.solicitud)
            .joinedload(Solicitud.vehiculo)
            .joinedload(Vehiculo.cliente)
            .joinedload(Cliente.usuario)
            .joinedload(User.persona),
            joinedload(Servicio.asignacion)
            .joinedload(Asignacion.proveedor_servicio)
            .joinedload(ProveedorServicio.usuario)
            .joinedload(User.persona),
        )
        .filter(Asignacion.id_taller == id_taller)
    )


def user_owns_taller(db: Session, id_taller: int, id_usuario: int) -> bool:
    return (
        db.query(Taller)
        .filter(Taller.id_taller == id_taller, Taller.id_usuario == id_usuario, Taller.activo.is_(True))
        .first()
        is not None
    )


def get_first_user_taller_id(db: Session, id_usuario: int) -> int | None:
    taller = (
        db.query(Taller)
        .filter(Taller.id_usuario == id_usuario, Taller.activo.is_(True))
        .order_by(Taller.id_taller)
        .first()
    )
    return taller.id_taller if taller else None


def get_service_history_report(db: Session, id_taller: int, filters: ReporteFilters) -> list[dict[str, Any]]:
    servicios = (
        _apply_common_filters(_base_service_query(db, id_taller), filters)
        .order_by(Servicio.fecha_inicio.desc().nullslast(), Servicio.id_servicio.desc())
        .limit(filters.limit)
        .all()
    )

    rows = []
    for servicio in servicios:
        asignacion = servicio.asignacion
        solicitud = asignacion.solicitud if asignacion else None
        vehiculo = solicitud.vehiculo if solicitud else None
        cliente = vehiculo.cliente if vehiculo else None
        proveedor = asignacion.proveedor_servicio if asignacion else None
        rows.append(
            {
                "fecha_inicio": _dt(servicio.fecha_inicio),
                "fecha_fin": _dt(servicio.fecha_fin),
                "cliente": cliente.usuario.persona.nombre_completo if cliente and cliente.usuario and cliente.usuario.persona else None,
                "vehiculo": f"{vehiculo.marca} {vehiculo.modelo}" if vehiculo else None,
                "placa": vehiculo.placa if vehiculo else None,
                "servicios": ", ".join(detalle.nombre for detalle in servicio.detalles_servicio) or solicitud.descripcion if solicitud else None,
                "tecnico": proveedor.usuario.persona.nombre_completo if proveedor and proveedor.usuario and proveedor.usuario.persona else None,
                "estado": servicio.estado,
                "total": _money(servicio.total),
            }
        )
    return rows


def get_service_income_report(db: Session, id_taller: int, filters: ReporteFilters) -> list[dict[str, Any]]:
    query = (
        db.query(
            func.date_trunc("month", Servicio.fecha_inicio).label("periodo"),
            func.count(Servicio.id_servicio).label("cantidad_servicios"),
            func.coalesce(func.sum(Servicio.total), 0).label("total_ingresos"),
            func.coalesce(func.avg(Servicio.total), 0).label("promedio_por_servicio"),
        )
        .join(Asignacion, Asignacion.id_asignacion == Servicio.id_asignacion)
        .join(Solicitud, Solicitud.id_solicitud == Asignacion.id_solicitud)
        .join(Vehiculo, Vehiculo.id_vehiculo == Solicitud.id_vehiculo)
        .join(Cliente, Cliente.id_cliente == Vehiculo.id_cliente)
        .outerjoin(ProveedorServicio, ProveedorServicio.id_proveedor == Asignacion.id_proveedor)
        .filter(Asignacion.id_taller == id_taller)
    )
    rows = (
        _apply_common_filters(query, filters)
        .group_by("periodo")
        .order_by("periodo")
        .limit(filters.limit)
        .all()
    )
    return [
        {
            "periodo": row.periodo.date().isoformat() if row.periodo else None,
            "cantidad_servicios": row.cantidad_servicios,
            "total_ingresos": _money(row.total_ingresos),
            "promedio_por_servicio": _money(row.promedio_por_servicio),
        }
        for row in rows
    ]


def get_top_services_report(db: Session, id_taller: int, filters: ReporteFilters) -> list[dict[str, Any]]:
    query = (
        db.query(
            DetalleServicio.nombre.label("servicio"),
            func.count(DetalleServicio.id_detalle_servicio).label("cantidad"),
            func.coalesce(func.sum(DetalleServicio.sub_total), 0).label("total_generado"),
        )
        .join(Servicio, Servicio.id_servicio == DetalleServicio.id_servicio)
        .join(Asignacion, Asignacion.id_asignacion == Servicio.id_asignacion)
        .join(Solicitud, Solicitud.id_solicitud == Asignacion.id_solicitud)
        .join(Vehiculo, Vehiculo.id_vehiculo == Solicitud.id_vehiculo)
        .join(Cliente, Cliente.id_cliente == Vehiculo.id_cliente)
        .outerjoin(ProveedorServicio, ProveedorServicio.id_proveedor == Asignacion.id_proveedor)
        .filter(Asignacion.id_taller == id_taller)
    )
    rows = (
        _apply_common_filters(query, filters)
        .group_by(DetalleServicio.nombre)
        .order_by(func.count(DetalleServicio.id_detalle_servicio).desc())
        .limit(filters.limit)
        .all()
    )
    total_cantidad = sum(row.cantidad for row in rows) or 1
    return [
        {
            "servicio": row.servicio,
            "cantidad": row.cantidad,
            "total_generado": _money(row.total_generado),
            "porcentaje": round((row.cantidad / total_cantidad) * 100, 2),
        }
        for row in rows
    ]


def get_customer_summary_report(db: Session, id_taller: int, filters: ReporteFilters) -> list[dict[str, Any]]:
    query = (
        db.query(
            Cliente.id_cliente,
            Persona.nombre_completo.label("cliente"),
            func.count(Servicio.id_servicio).label("cantidad_servicios"),
            func.coalesce(func.sum(Servicio.total), 0).label("total_gastado"),
            func.max(Servicio.fecha_inicio).label("ultimo_servicio"),
        )
        .join(User, User.id_usuario == Cliente.id_usuario)
        .join(Persona, Persona.id_persona == User.id_persona)
        .join(Vehiculo, Vehiculo.id_cliente == Cliente.id_cliente)
        .join(Solicitud, Solicitud.id_vehiculo == Vehiculo.id_vehiculo)
        .join(Asignacion, Asignacion.id_solicitud == Solicitud.id_solicitud)
        .join(Servicio, Servicio.id_asignacion == Asignacion.id_asignacion)
        .outerjoin(ProveedorServicio, ProveedorServicio.id_proveedor == Asignacion.id_proveedor)
        .filter(Asignacion.id_taller == id_taller)
    )
    rows = (
        _apply_common_filters(query, filters)
        .group_by(Cliente.id_cliente, Persona.nombre_completo)
        .order_by(func.coalesce(func.sum(Servicio.total), 0).desc())
        .limit(filters.limit)
        .all()
    )
    return [
        {
            "id_cliente": row.id_cliente,
            "cliente": row.cliente,
            "cantidad_servicios": row.cantidad_servicios,
            "total_gastado": _money(row.total_gastado),
            "ultimo_servicio": _dt(row.ultimo_servicio),
        }
        for row in rows
    ]


def get_vehicle_history_report(db: Session, id_taller: int, filters: ReporteFilters) -> list[dict[str, Any]]:
    return get_service_history_report(db, id_taller, filters)


def get_pending_services_report(db: Session, id_taller: int, filters: ReporteFilters) -> list[dict[str, Any]]:
    pending_filters = filters.model_copy()
    if not pending_filters.status:
        pending_filters.status = None
    rows = get_service_history_report(db, id_taller, pending_filters)
    if filters.status:
        return rows
    return [row for row in rows if str(row.get("estado") or "").lower() not in {"finalizado", "completado", "pagado", "anulado", "cancelado"}]


def get_technician_productivity_report(db: Session, id_taller: int, filters: ReporteFilters) -> list[dict[str, Any]]:
    servicios = _apply_common_filters(_base_service_query(db, id_taller), filters).limit(1000).all()
    grouped: dict[int, dict[str, Any]] = defaultdict(
        lambda: {
            "tecnico": "Sin asignar",
            "cantidad_servicios": 0,
            "servicios_completados": 0,
            "servicios_pendientes": 0,
            "total_generado": 0.0,
        }
    )
    for servicio in servicios:
        proveedor = servicio.asignacion.proveedor_servicio if servicio.asignacion else None
        key = proveedor.id_proveedor if proveedor else 0
        row = grouped[key]
        if proveedor and proveedor.usuario and proveedor.usuario.persona:
            row["tecnico"] = proveedor.usuario.persona.nombre_completo
        row["cantidad_servicios"] += 1
        if str(servicio.estado).lower() in {"finalizado", "completado", "pagado"}:
            row["servicios_completados"] += 1
        else:
            row["servicios_pendientes"] += 1
        row["total_generado"] += _money(servicio.total)
    return sorted(grouped.values(), key=lambda item: item["cantidad_servicios"], reverse=True)[: filters.limit]


def get_service_status_summary_report(db: Session, id_taller: int, filters: ReporteFilters) -> list[dict[str, Any]]:
    query = (
        db.query(Servicio.estado, func.count(Servicio.id_servicio).label("cantidad"))
        .join(Asignacion, Asignacion.id_asignacion == Servicio.id_asignacion)
        .join(Solicitud, Solicitud.id_solicitud == Asignacion.id_solicitud)
        .join(Vehiculo, Vehiculo.id_vehiculo == Solicitud.id_vehiculo)
        .join(Cliente, Cliente.id_cliente == Vehiculo.id_cliente)
        .outerjoin(ProveedorServicio, ProveedorServicio.id_proveedor == Asignacion.id_proveedor)
        .filter(Asignacion.id_taller == id_taller)
    )
    rows = (
        _apply_common_filters(query, filters)
        .group_by(Servicio.estado)
        .order_by(func.count(Servicio.id_servicio).desc())
        .limit(filters.limit)
        .all()
    )
    total = sum(row.cantidad for row in rows) or 1
    return [
        {
            "estado": row.estado,
            "cantidad": row.cantidad,
            "porcentaje": round((row.cantidad / total) * 100, 2),
        }
        for row in rows
    ]
