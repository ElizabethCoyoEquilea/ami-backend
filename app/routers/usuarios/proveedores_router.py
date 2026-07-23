from datetime import datetime, timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.solicitudes.asignacion import Asignacion
from app.models.solicitudes.calificacion import Calificacion
from app.models.solicitudes.pago import Pago
from app.models.solicitudes.servicio import Servicio
from app.models.solicitudes.solicitud import Solicitud
from app.models.usuarios.persona import Persona
from app.models.usuarios.cliente import Cliente
from app.models.usuarios.proveedor_servicio import ProveedorServicio
from app.models.usuarios.usuario import User
from app.models.usuarios.vehiculo import Vehiculo

router = APIRouter(prefix="/proveedores", tags=["Proveedores"])


class CambiarEstadoProveedorRequest(BaseModel):
    estado: str  # "Disponible", "Ocupado", "Fuera de servicio"


class CambiarEstadoProveedorResponse(BaseModel):
    id_proveedor: int
    estado: str
    mensaje: str


@router.patch("/mi-estado", response_model=CambiarEstadoProveedorResponse, status_code=status.HTTP_200_OK)
def cambiar_estado_proveedor(
    request: CambiarEstadoProveedorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    proveedor = (
        db.query(ProveedorServicio)
        .filter(ProveedorServicio.id_usuario == current_user.id_usuario)
        .first()
    )
    if not proveedor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario actual no esta registrado como proveedor de servicio",
        )

    nuevo_estado = request.estado.strip()
    if nuevo_estado.lower() in ("disponible", "activo", "online"):
        nuevo_estado = "Disponible"
    elif nuevo_estado.lower() in ("ocupado", "en_servicio", "buscando"):
        nuevo_estado = "Ocupado"
    else:
        nuevo_estado = "Fuera de servicio"

    proveedor.estado = nuevo_estado
    db.commit()
    db.refresh(proveedor)

    return CambiarEstadoProveedorResponse(
        id_proveedor=proveedor.id_proveedor,
        estado=proveedor.estado,
        mensaje=f"Estado actualizado a '{proveedor.estado}' exitosamente",
    )


@router.get("/mi-estado", status_code=status.HTTP_200_OK)
def obtener_estado_proveedor(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    proveedor = (
        db.query(ProveedorServicio)
        .filter(ProveedorServicio.id_usuario == current_user.id_usuario)
        .first()
    )
    if not proveedor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario actual no esta registrado como proveedor de servicio",
        )
    return {"id_proveedor": proveedor.id_proveedor, "estado": proveedor.estado}


@router.get("/mis-ganancias", status_code=status.HTTP_200_OK)
def obtener_mis_ganancias(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    proveedor = (
        db.query(ProveedorServicio)
        .filter(ProveedorServicio.id_usuario == current_user.id_usuario)
        .first()
    )
    if not proveedor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El usuario actual no esta registrado como proveedor de servicio",
        )

    id_p = proveedor.id_proveedor
    ahora = datetime.now()
    inicio_hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(hours=4)
    fin_hoy = inicio_hoy + timedelta(days=1)

    # Calculate earnings today
    ganancias_hoy = (
        db.query(func.coalesce(func.sum(Pago.monto), 0))
        .join(Servicio, Servicio.id_pago == Pago.id_pago)
        .join(Asignacion, Asignacion.id_asignacion == Servicio.id_asignacion)
        .filter(
            Asignacion.id_proveedor == id_p,
            func.lower(Servicio.estado).in_(["pagado", "finalizado", "completado"]),
            func.coalesce(Servicio.fecha_fin, Servicio.fecha_inicio, Asignacion.fecha_inicio) >= inicio_hoy,
            func.coalesce(Servicio.fecha_fin, Servicio.fecha_inicio, Asignacion.fecha_inicio) <= fin_hoy,
            func.lower(Pago.estado).in_(["pagado", "completado"]),
        )
        .scalar()
        or 0
    )

    # Calculate total earnings
    ganancias_totales = (
        db.query(func.coalesce(func.sum(Pago.monto), 0))
        .join(Servicio, Servicio.id_pago == Pago.id_pago)
        .join(Asignacion, Asignacion.id_asignacion == Servicio.id_asignacion)
        .filter(
            Asignacion.id_proveedor == id_p,
            func.lower(Servicio.estado).in_(["pagado", "finalizado", "completado"]),
            func.lower(Pago.estado).in_(["pagado", "completado"]),
        )
        .scalar()
        or 0
    )

    # Count completed services today
    servicios_hoy = (
        db.query(func.count(Servicio.id_servicio))
        .join(Asignacion, Asignacion.id_asignacion == Servicio.id_asignacion)
        .filter(
            Asignacion.id_proveedor == id_p,
            func.lower(Servicio.estado).in_(["pagado", "finalizado", "completado"]),
            func.coalesce(Servicio.fecha_fin, Servicio.fecha_inicio, Asignacion.fecha_inicio) >= inicio_hoy,
            func.coalesce(Servicio.fecha_fin, Servicio.fecha_inicio, Asignacion.fecha_inicio) <= fin_hoy,
        )
        .scalar()
        or 0
    )

    # Count total completed services
    servicios_totales = (
        db.query(func.count(Servicio.id_servicio))
        .join(Asignacion, Asignacion.id_asignacion == Servicio.id_asignacion)
        .filter(
            Asignacion.id_proveedor == id_p,
            func.lower(Servicio.estado).in_(["pagado", "finalizado", "completado"]),
        )
        .scalar()
        or 0
    )

    # Calculate average rating received by this provider
    calificacion_data = (
        db.query(
            func.coalesce(func.avg(Calificacion.puntuacion), 0),
            func.count(Calificacion.id_calificacion),
        )
        .join(Servicio, Servicio.id_servicio == Calificacion.id_servicio)
        .join(Asignacion, Asignacion.id_asignacion == Servicio.id_asignacion)
        .filter(Asignacion.id_proveedor == id_p)
        .first()
    )

    # List of detailed services
    services_rows = (
        db.query(
            Servicio.id_servicio,
            func.coalesce(Servicio.fecha_fin, Servicio.fecha_inicio, Asignacion.fecha_inicio).label("fecha"),
            Persona.nombre_completo.label("cliente_nombre"),
            Vehiculo.marca,
            Vehiculo.modelo,
            Vehiculo.placa,
            Pago.monto,
            Servicio.estado,
            Calificacion.puntuacion,
            Calificacion.comentario,
        )
        .join(Asignacion, Asignacion.id_asignacion == Servicio.id_asignacion)
        .join(Solicitud, Solicitud.id_solicitud == Asignacion.id_solicitud)
        .join(Vehiculo, Vehiculo.id_vehiculo == Solicitud.id_vehiculo)
        .join(Cliente, Cliente.id_cliente == Vehiculo.id_cliente)
        .join(User, User.id_usuario == Cliente.id_usuario)
        .outerjoin(Persona, Persona.id_persona == User.id_persona)
        .outerjoin(Pago, Pago.id_pago == Servicio.id_pago)
        .outerjoin(Calificacion, Calificacion.id_servicio == Servicio.id_servicio)
        .filter(Asignacion.id_proveedor == id_p)
        .order_by(Servicio.id_servicio.desc())
        .limit(50)
        .all()
    )

    lista_servicios = []
    for r in services_rows:
        vehiculo_str = f"{r.marca or ''} {r.modelo or ''} [{r.placa or ''}]".strip()
        lista_servicios.append({
            "id_servicio": r.id_servicio,
            "fecha": r.fecha.isoformat() if r.fecha else None,
            "cliente_nombre": r.cliente_nombre or "Cliente",
            "vehiculo": vehiculo_str,
            "monto": float(r.monto or 0),
            "estado": r.estado,
            "puntuacion": float(r.puntuacion) if r.puntuacion is not None else None,
            "comentario": r.comentario,
        })

    return {
        "id_proveedor": id_p,
        "estado_actual": proveedor.estado,
        "resumen": {
            "ganancias_hoy": float(ganancias_hoy),
            "ganancias_totales": float(ganancias_totales),
            "servicios_finalizados_hoy": int(servicios_hoy),
            "servicios_totales": int(servicios_totales),
            "calificacion_promedio": round(float(calificacion_data[0] or 0), 1),
            "total_calificaciones": int(calificacion_data[1] or 0),
        },
        "servicios": lista_servicios,
    }
