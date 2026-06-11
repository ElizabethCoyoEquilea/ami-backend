from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.solicitudes.cotizacion import Invitacion
from app.models.usuarios.usuario import User
from app.repositories.cotizaciones_repository import (
    aceptar_invitacion_cliente,
    create_invitacion_pendiente,
    get_invitacion_detalle_by_id,
    list_invitaciones_pendientes_by_taller,
    rechazar_invitacion_cliente,
)
from app.repositories.solicitudes_repository import get_solicitud_by_id
from app.repositories.talleres_repository import get_active_taller_by_id
from app.websockets.connection_manager import clients_ws_manager


def registrar_invitacion_pendiente(
    db: Session,
    id_solicitud: int,
    id_taller: int,
) -> Invitacion:
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

    invitacion_pendiente = (
        db.query(Invitacion)
        .filter(
            Invitacion.id_solicitud == id_solicitud,
            Invitacion.estado.in_(["pendiente", "enviado"]),
        )
        .first()
    )
    if invitacion_pendiente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una invitacion pendiente o enviada para esta solicitud",
        )

    invitacion_aceptada = (
        db.query(Invitacion)
        .filter(
            Invitacion.id_solicitud == id_solicitud,
            Invitacion.estado.in_(["aceptada", "aceptado"]),
        )
        .first()
    )
    if invitacion_aceptada:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una invitacion aceptada para esta solicitud",
        )

    try:
        return create_invitacion_pendiente(db, solicitud, id_taller)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo crear la invitacion",
        )


def listar_invitaciones_pendientes_taller(
    db: Session,
    id_taller: int,
    current_user: User,
) -> list[Invitacion]:
    taller = get_active_taller_by_id(db, id_taller)
    if not taller or taller.id_usuario != current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taller no encontrado",
        )

    return list_invitaciones_pendientes_by_taller(db, id_taller)


def obtener_invitacion_por_id(
    db: Session,
    id_invitacion: int,
    current_user: User,
) -> Invitacion:
    invitacion = get_invitacion_detalle_by_id(db, id_invitacion)
    if not invitacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitacion no encontrada",
        )

    es_admin_taller = bool(invitacion.taller and invitacion.taller.id_usuario == current_user.id_usuario)
    cliente = invitacion.solicitud.vehiculo.cliente if invitacion.solicitud and invitacion.solicitud.vehiculo else None
    es_cliente_dueno = bool(cliente and cliente.id_usuario == current_user.id_usuario)

    if not es_admin_taller and not es_cliente_dueno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitacion no encontrada para el usuario autenticado",
        )

    return invitacion


async def rechazar_invitacion_por_solicitud(
    db: Session,
    id_solicitud: int,
    id_invitacion: int,
) -> dict:
    invitacion = get_invitacion_detalle_by_id(db, id_invitacion)
    if not invitacion or invitacion.id_solicitud != id_solicitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitacion no encontrada para la solicitud indicada",
        )

    cliente = invitacion.solicitud.vehiculo.cliente if invitacion.solicitud.vehiculo else None
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado para la solicitud indicada",
        )

    try:
        invitacion_rechazada = rechazar_invitacion_cliente(db, invitacion)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo rechazar la invitacion",
        )

    websocket_enviado = await clients_ws_manager.send_to_user(
        cliente.id_usuario,
        {
            "tipo": "rechazo administrador",
            "data": {
                "id_solicitud": invitacion_rechazada.id_solicitud,
                "id_invitacion": invitacion_rechazada.id_invitacion,
                "id_taller": invitacion_rechazada.id_taller,
                "estado_invitacion": invitacion_rechazada.estado,
                "estado_solicitud": "pendiente",
            },
        },
    )

    return {
        "id_invitacion": invitacion_rechazada.id_invitacion,
        "id_solicitud": invitacion_rechazada.id_solicitud,
        "id_taller": invitacion_rechazada.id_taller,
        "numero_ronda": invitacion_rechazada.numero_ronda,
        "estado": invitacion_rechazada.estado,
        "fecha_hora_envio": invitacion_rechazada.fecha_hora_envio,
        "fecha_hora_expiracion": invitacion_rechazada.fecha_hora_expiracion,
        "fecha_hora_respuesta": invitacion_rechazada.fecha_hora_respuesta,
        "websocket_enviado": websocket_enviado,
    }


def procesar_respuesta_invitacion_cliente(
    db: Session,
    id_usuario_cliente: int,
    mensaje: dict,
) -> dict:
    tipo = mensaje.get("tipo")
    data = mensaje.get("data") or {}

    if tipo not in {"aceptar_invitacion", "rechazar_invitacion"}:
        return {
            "tipo": "error",
            "data": {
                "mensaje": "Tipo de mensaje no soportado",
            },
        }

    id_solicitud = data.get("id_solicitud")
    id_invitacion = data.get("id_invitacion")

    if not id_solicitud or not id_invitacion:
        return {
            "tipo": "error",
            "data": {
                "mensaje": "id_solicitud e id_invitacion son obligatorios",
            },
        }

    try:
        id_solicitud = int(id_solicitud)
        id_invitacion = int(id_invitacion)
    except (TypeError, ValueError):
        return {
            "tipo": "error",
            "data": {
                "mensaje": "id_solicitud e id_invitacion deben ser numeros",
            },
        }

    invitacion = get_invitacion_detalle_by_id(db, id_invitacion)
    if not invitacion or invitacion.id_solicitud != id_solicitud:
        return {
            "tipo": "error",
            "data": {
                "mensaje": "Invitacion no encontrada",
            },
        }

    cliente = invitacion.solicitud.vehiculo.cliente if invitacion.solicitud.vehiculo else None
    if not cliente or cliente.id_usuario != id_usuario_cliente:
        return {
            "tipo": "error",
            "data": {
                "mensaje": "Invitacion no pertenece al cliente autenticado",
            },
        }

    if invitacion.estado not in {"pendiente", "enviado"}:
        return {
            "tipo": "error",
            "data": {
                "mensaje": "La invitacion ya fue respondida",
            },
        }

    if tipo == "aceptar_invitacion":
        try:
            asignacion = aceptar_invitacion_cliente(db, invitacion)
        except SQLAlchemyError:
            return {
                "tipo": "error",
                "data": {
                    "mensaje": "No se pudo aceptar la invitacion",
                },
            }

        return {
            "tipo": "invitacion_aceptada",
            "data": {
                "id_solicitud": invitacion.id_solicitud,
                "id_invitacion": invitacion.id_invitacion,
                "id_taller": invitacion.id_taller,
                "id_asignacion": asignacion.id_asignacion,
                "estado_invitacion": "aceptada",
                "estado_solicitud": "aceptada",
                "estado_asignacion": asignacion.estado,
            },
        }

    try:
        invitacion_rechazada = rechazar_invitacion_cliente(db, invitacion)
    except SQLAlchemyError:
        return {
            "tipo": "error",
            "data": {
                "mensaje": "No se pudo rechazar la invitacion",
            },
        }

    return {
        "tipo": "invitacion_rechazada",
        "data": {
            "id_solicitud": invitacion_rechazada.id_solicitud,
            "id_invitacion": invitacion_rechazada.id_invitacion,
            "id_taller": invitacion_rechazada.id_taller,
            "estado_invitacion": "rechazada",
            "estado_solicitud": "pendiente",
        },
    }
