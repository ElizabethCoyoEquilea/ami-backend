from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.models.solicitudes.asignacion import Asignacion
from app.models.solicitudes.cotizacion import Invitacion
from app.models.solicitudes.servicio import Servicio
from app.models.solicitudes.solicitud import Solicitud
from app.repositories.asignaciones_repository import (
    get_asignacion_detalle_by_id,
    get_asignacion_detalle_by_solicitud_id,
)
from app.repositories.talleres_repository import get_active_provider_assignment_by_user_and_taller
from app.schemas.solicitudes.asignacion_schema import (
    ConfirmarLlegadaRequest,
    IniciarRecorridoRequest,
)
from app.services.notificaciones_service import (
    notificar_en_camino_a_cliente,
    notificar_proveedor_llego_a_cliente,
)
from app.models.usuarios.vehiculo import Vehiculo


def _calcular_minutos_desde(fecha_inicio: datetime) -> Decimal:
    ahora = datetime.now(tz=fecha_inicio.tzinfo) if fecha_inicio.tzinfo else datetime.now()
    minutos = max((ahora - fecha_inicio).total_seconds() / 60, 0)
    return Decimal(str(minutos)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def obtener_asignacion_por_id(
    db: Session,
    id_asignacion: int,
) -> Asignacion:
    asignacion = get_asignacion_detalle_by_id(db, id_asignacion)
    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignacion no encontrada",
        )

    return asignacion


def obtener_asignacion_por_solicitud(
    db: Session,
    id_solicitud: int,
) -> Asignacion:
    asignacion = get_asignacion_detalle_by_solicitud_id(db, id_solicitud)
    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignacion no encontrada para la solicitud indicada",
        )

    return asignacion


async def iniciar_recorrido_asignacion(
    db: Session,
    data: IniciarRecorridoRequest,
    id_usuario: int,
) -> dict:
    proveedor_actual = get_active_provider_assignment_by_user_and_taller(
        db,
        id_usuario,
        data.id_taller,
    )
    if not proveedor_actual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe proveedor activo para el usuario autenticado en el taller",
        )

    asignacion = (
        db.query(Asignacion)
        .filter(
            Asignacion.id_asignacion == data.id_asignacion,
            Asignacion.id_solicitud == data.id_solicitud,
            Asignacion.id_taller == data.id_taller,
        )
        .first()
    )
    invitacion = (
        db.query(Invitacion)
        .filter(
            Invitacion.id_invitacion == data.id_invitacion,
            Invitacion.id_solicitud == data.id_solicitud,
            Invitacion.id_taller == data.id_taller,
        )
        .first()
    )
    solicitud = (
        db.query(Solicitud)
        .options(joinedload(Solicitud.vehiculo).joinedload(Vehiculo.cliente))
        .filter(Solicitud.id_solicitud == data.id_solicitud)
        .first()
    )

    if not asignacion or not invitacion or not solicitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignacion, solicitud o invitacion no encontrada",
        )

    if asignacion.id_proveedor != proveedor_actual.id_proveedor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La asignacion no pertenece al proveedor autenticado",
        )

    try:
        asignacion.estado = "en_camino"
        db.commit()
        db.refresh(asignacion)
        db.refresh(solicitud)
        db.refresh(invitacion)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo iniciar el recorrido",
        )

    websocket_enviado = await notificar_en_camino_a_cliente(solicitud)

    return {
        "id_asignacion": asignacion.id_asignacion,
        "id_solicitud": solicitud.id_solicitud,
        "id_invitacion": invitacion.id_invitacion,
        "id_taller": asignacion.id_taller,
        "id_proveedor": asignacion.id_proveedor,
        "estado_asignacion": asignacion.estado,
        "websocket_enviado": websocket_enviado,
    }


async def confirmar_llegada_asignacion(
    db: Session,
    data: ConfirmarLlegadaRequest,
    id_usuario: int,
) -> dict:
    proveedor_actual = get_active_provider_assignment_by_user_and_taller(
        db,
        id_usuario,
        data.id_taller,
    )
    if not proveedor_actual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No existe proveedor activo para el usuario autenticado en el taller",
        )

    asignacion = (
        db.query(Asignacion)
        .filter(
            Asignacion.id_asignacion == data.id_asignacion,
            Asignacion.id_solicitud == data.id_solicitud,
            Asignacion.id_taller == data.id_taller,
        )
        .first()
    )
    invitacion = (
        db.query(Invitacion)
        .filter(
            Invitacion.id_invitacion == data.id_invitacion,
            Invitacion.id_solicitud == data.id_solicitud,
            Invitacion.id_taller == data.id_taller,
        )
        .first()
    )
    solicitud = (
        db.query(Solicitud)
        .options(joinedload(Solicitud.vehiculo).joinedload(Vehiculo.cliente))
        .filter(Solicitud.id_solicitud == data.id_solicitud)
        .first()
    )

    if not asignacion or not invitacion or not solicitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignacion, solicitud o invitacion no encontrada",
        )

    if asignacion.id_proveedor != proveedor_actual.id_proveedor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La asignacion no pertenece al proveedor autenticado",
        )

    try:
        asignacion.estado = "llego_al_lugar"
        asignacion.tiempo_llegada = _calcular_minutos_desde(asignacion.fecha_inicio)
        servicio = Servicio(
            id_asignacion=asignacion.id_asignacion,
            fecha_inicio=datetime.now(),
            estado="en_proceso",
            total=Decimal("0.00"),
        )
        db.add(servicio)
        db.commit()
        db.refresh(asignacion)
        db.refresh(solicitud)
        db.refresh(invitacion)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo confirmar la llegada",
        )

    await notificar_proveedor_llego_a_cliente(solicitud)

    return {
        "id_asignacion": asignacion.id_asignacion,
        "id_solicitud": asignacion.id_solicitud,
        "id_invitacion": invitacion.id_invitacion,
        "id_taller": asignacion.id_taller,
        "id_proveedor": asignacion.id_proveedor,
        "estado_asignacion": asignacion.estado,
        "tiempo_llegada": asignacion.tiempo_llegada,
    }
