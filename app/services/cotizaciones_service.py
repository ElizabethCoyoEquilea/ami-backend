from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.solicitudes.cotizacion import Cotizacion
from app.models.usuarios.usuario import User
from app.repositories.cotizaciones_repository import (
    aceptar_cotizacion_cliente,
    create_cotizacion_pendiente,
    get_cotizacion_detalle_by_id,
    get_cotizacion_finalizada_by_solicitud,
    list_cotizaciones_pendientes_by_taller,
    rechazar_cotizacion_cliente,
    update_monto_cotizacion_admin,
)
from app.repositories.solicitudes_repository import get_solicitud_by_id
from app.repositories.talleres_repository import get_active_taller_by_id
from app.websockets.connection_manager import clients_ws_manager


def registrar_cotizacion_pendiente(
    db: Session,
    id_solicitud: int,
    id_taller: int,
) -> Cotizacion:
    solicitud = get_solicitud_by_id(db, id_solicitud)
    if not solicitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada",
        )

    taller = get_active_taller_by_id(db, id_taller)
    if not taller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taller no encontrado",
        )

    cotizacion_existente = get_cotizacion_finalizada_by_solicitud(
        db,
        id_solicitud,
    )
    if cotizacion_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una cotizacion aceptada o rechazada para esta solicitud",
        )

    try:
        return create_cotizacion_pendiente(db, solicitud, id_taller)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo crear la cotizacion",
        )


def listar_cotizaciones_pendientes_taller(
    db: Session,
    id_taller: int,
    current_user: User,
) -> list[Cotizacion]:
    taller = get_active_taller_by_id(db, id_taller)
    if not taller or taller.id_usuario != current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taller no encontrado",
        )

    return list_cotizaciones_pendientes_by_taller(db, id_taller)


async def rechazar_cotizacion_por_solicitud(
    db: Session,
    id_solicitud: int,
    id_cotizacion: int,
) -> dict:
    cotizacion = get_cotizacion_detalle_by_id(db, id_cotizacion)
    if not cotizacion or cotizacion.id_solicitud != id_solicitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cotizacion no encontrada para la solicitud indicada",
        )

    cliente = cotizacion.solicitud.vehiculo.cliente if cotizacion.solicitud.vehiculo else None
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado para la solicitud indicada",
        )

    try:
        cotizacion_rechazada = rechazar_cotizacion_cliente(db, cotizacion)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo rechazar la cotizacion",
        )

    websocket_enviado = await clients_ws_manager.send_to_user(
        cliente.id_usuario,
        {
            "tipo": "rechazo administrador",
            "data": {
                "id_solicitud": cotizacion_rechazada.id_solicitud,
                "id_cotizacion": cotizacion_rechazada.id_cotizacion,
                "id_taller": cotizacion_rechazada.id_taller,
                "estado_cotizacion": cotizacion_rechazada.estado,
                "estado_solicitud": "pendiente",
            },
        },
    )

    return {
        "id_cotizacion": cotizacion_rechazada.id_cotizacion,
        "id_solicitud": cotizacion_rechazada.id_solicitud,
        "id_taller": cotizacion_rechazada.id_taller,
        "monto": cotizacion_rechazada.monto,
        "estado": cotizacion_rechazada.estado,
        "websocket_enviado": websocket_enviado,
    }


async def enviar_monto_cotizacion_admin(
    db: Session,
    id_solicitud: int,
    id_cotizacion: int,
    id_vehiculo: int,
    monto: Decimal,
    current_user: User,
) -> dict:
    cotizacion = get_cotizacion_detalle_by_id(db, id_cotizacion)
    if not cotizacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cotizacion no encontrada",
        )

    if cotizacion.id_solicitud != id_solicitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cotizacion no encontrada para la solicitud indicada",
        )

    if not cotizacion.solicitud or cotizacion.solicitud.id_vehiculo != id_vehiculo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada para el vehiculo indicado",
        )

    if not cotizacion.taller or cotizacion.taller.id_usuario != current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cotizacion no encontrada para el usuario autenticado",
        )

    cliente = cotizacion.solicitud.vehiculo.cliente if cotizacion.solicitud.vehiculo else None
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado para el vehiculo indicado",
        )

    id_usuario_cliente = cliente.id_usuario

    try:
        cotizacion_actualizada = update_monto_cotizacion_admin(db, cotizacion, monto)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo actualizar la cotizacion",
        )

    websocket_enviado = await clients_ws_manager.send_to_user(
        id_usuario_cliente,
        {
            "tipo": "cotizacion del administrador",
            "data": {
                "id_solicitud": id_solicitud,
                "id_cotizacion": id_cotizacion,
                "monto": float(cotizacion_actualizada.monto),
            },
        },
    )

    return {
        "id_cotizacion": cotizacion_actualizada.id_cotizacion,
        "id_solicitud": cotizacion_actualizada.id_solicitud,
        "id_taller": cotizacion_actualizada.id_taller,
        "monto": cotizacion_actualizada.monto,
        "estado": cotizacion_actualizada.estado,
        "websocket_enviado": websocket_enviado,
    }


def procesar_respuesta_cotizacion_cliente(
    db: Session,
    id_usuario_cliente: int,
    mensaje: dict,
) -> dict:
    tipo = mensaje.get("tipo")
    data = mensaje.get("data") or {}

    if tipo not in {"aceptar_cotizacion", "rechazar_cotizacion"}:
        return {
            "tipo": "error",
            "data": {
                "mensaje": "Tipo de mensaje no soportado",
            },
        }

    id_solicitud = data.get("id_solicitud")
    id_cotizacion = data.get("id_cotizacion")

    if not id_solicitud or not id_cotizacion:
        return {
            "tipo": "error",
            "data": {
                "mensaje": "id_solicitud e id_cotizacion son obligatorios",
            },
        }

    try:
        id_solicitud = int(id_solicitud)
        id_cotizacion = int(id_cotizacion)
    except (TypeError, ValueError):
        return {
            "tipo": "error",
            "data": {
                "mensaje": "id_solicitud e id_cotizacion deben ser numeros",
            },
        }

    cotizacion = get_cotizacion_detalle_by_id(db, id_cotizacion)
    if not cotizacion or cotizacion.id_solicitud != id_solicitud:
        return {
            "tipo": "error",
            "data": {
                "mensaje": "Cotizacion no encontrada",
            },
        }

    cliente = cotizacion.solicitud.vehiculo.cliente if cotizacion.solicitud.vehiculo else None
    if not cliente or cliente.id_usuario != id_usuario_cliente:
        return {
            "tipo": "error",
            "data": {
                "mensaje": "Cotizacion no pertenece al cliente autenticado",
            },
        }

    if cotizacion.estado != "pendiente":
        return {
            "tipo": "error",
            "data": {
                "mensaje": "La cotizacion ya fue respondida",
            },
        }

    if tipo == "aceptar_cotizacion":
        try:
            asignacion = aceptar_cotizacion_cliente(db, cotizacion)
        except SQLAlchemyError:
            return {
                "tipo": "error",
                "data": {
                    "mensaje": "No se pudo aceptar la cotizacion",
                },
            }

        return {
            "tipo": "cotizacion_aceptada",
            "data": {
                "id_solicitud": cotizacion.id_solicitud,
                "id_cotizacion": cotizacion.id_cotizacion,
                "id_taller": cotizacion.id_taller,
                "id_asignacion": asignacion.id_asignacion,
                "estado_cotizacion": "aceptada",
                "estado_solicitud": "aceptada",
                "estado_asignacion": asignacion.estado,
            },
        }

    try:
        cotizacion_rechazada = rechazar_cotizacion_cliente(db, cotizacion)
    except SQLAlchemyError:
        return {
            "tipo": "error",
            "data": {
                "mensaje": "No se pudo rechazar la cotizacion",
            },
        }

    return {
        "tipo": "cotizacion_rechazada",
        "data": {
            "id_solicitud": cotizacion_rechazada.id_solicitud,
            "id_cotizacion": cotizacion_rechazada.id_cotizacion,
            "id_taller": cotizacion_rechazada.id_taller,
            "estado_cotizacion": "rechazada",
            "estado_solicitud": "pendiente",
        },
    }
