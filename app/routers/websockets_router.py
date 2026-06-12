import logging
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from jose import JWTError
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionLocal
from app.core.security import verify_token
from app.models.solicitudes.asignacion import Asignacion
from app.models.solicitudes.cotizacion import Invitacion
from app.models.solicitudes.servicio import Servicio
from app.models.solicitudes.solicitud import Solicitud
from app.models.usuarios.usuario import User
from app.repositories.talleres_repository import (
    get_active_provider_assignment_by_user_and_taller,
    get_active_taller_by_id,
    get_asignacion_with_solicitud_by_id,
    list_active_provider_assignments_by_user,
    list_talleres_by_usuario,
)
from app.services.cotizaciones_service import (
    procesar_respuesta_invitacion_cliente,
    registrar_invitacion_pendiente,
)
from app.services.notificaciones_service import (
    notificar_solicitud_aceptada_a_proveedores_taller,
    notificar_solicitud_asignada_a_cliente,
)
from app.services.usuarios_service import get_current_provider_profile
from app.websockets.connection_manager import clients_ws_manager, providers_ws_manager


router = APIRouter(tags=["WebSockets"])
logger = logging.getLogger("ws_proveedor")


async def _send_provider_json(websocket: WebSocket, id_usuario: int, payload: dict) -> None:
    logger.info("send_to_user=%s payload=%s", id_usuario, payload)
    await websocket.send_json(payload)


async def _send_client_json(websocket: WebSocket, id_usuario: int, payload: dict) -> None:
    logger.info("clients_send_to_user=%s payload=%s", id_usuario, payload)
    await websocket.send_json(payload)


@router.websocket("/ws/clients")
async def websocket_clients(websocket: WebSocket, token: str):
    db = SessionLocal()
    id_usuario: int | None = None

    try:
        payload = verify_token(token)
        id_usuario = int(payload.get("sub"))
        usuario = (
            db.query(User)
            .filter(User.id_usuario == id_usuario, User.activo.is_(True))
            .first()
        )
        if not usuario:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await clients_ws_manager.connect(id_usuario, websocket)
        logger.info("clients_connection_open user=%s", id_usuario)

        while True:
            mensaje = await websocket.receive_json()
            logger.info("clients_message_received user=%s payload=%s", id_usuario, mensaje)

            if mensaje.get("tipo") == "seleccion_taller":
                data = mensaje.get("data") or {}
                id_solicitud = data.get("id_solicitud")
                id_taller = data.get("id_taller")

                try:
                    id_solicitud = int(id_solicitud)
                    id_taller = int(id_taller)
                except (TypeError, ValueError):
                    error_payload = {
                        "tipo": "error",
                        "data": {
                            "mensaje": "id_solicitud e id_taller deben ser numeros",
                        },
                    }
                    await _send_client_json(websocket, id_usuario, error_payload)
                    continue

                try:
                    invitacion = registrar_invitacion_pendiente(
                        db,
                        id_solicitud,
                        id_taller,
                    )
                except HTTPException as exc:
                    error_payload = {
                        "tipo": "error",
                        "data": {
                            "mensaje": exc.detail,
                        },
                    }
                    await _send_client_json(websocket, id_usuario, error_payload)
                    continue

                taller = get_active_taller_by_id(db, id_taller)
                if taller:
                    admin_payload = {
                        "tipo": "nueva_invitacion",
                        "data": {
                            "id_solicitud": invitacion.id_solicitud,
                            "id_taller": invitacion.id_taller,
                            "id_invitacion": invitacion.id_invitacion,
                            "estado_invitacion": invitacion.estado,
                        },
                    }
                    admin_notificado = await clients_ws_manager.send_to_user(
                        taller.id_usuario,
                        admin_payload,
                    )
                    logger.info(
                        "clients_new_invitacion_admin_notified user=%s event=%s notified=%s id_invitacion=%s",
                        taller.id_usuario,
                        admin_payload["tipo"],
                        admin_notificado,
                        invitacion.id_invitacion,
                    )

                resultado_payload = {
                    "tipo": "invitacion_creada",
                    "data": {
                        "id_invitacion": invitacion.id_invitacion,
                        "id_solicitud": invitacion.id_solicitud,
                        "id_taller": invitacion.id_taller,
                        "numero_ronda": invitacion.numero_ronda,
                        "estado": invitacion.estado,
                    },
                }
                await _send_client_json(websocket, id_usuario, resultado_payload)
                continue

            if mensaje.get("tipo") == "ubicacion_mecanico_actualizada":
                data = mensaje.get("data") or {}
                id_usuario_cliente = data.get("id_usuario_cliente")

                try:
                    id_usuario_cliente = int(id_usuario_cliente)
                except (TypeError, ValueError):
                    error_payload = {
                        "tipo": "error",
                        "data": {
                            "mensaje": "id_usuario_cliente debe ser numero",
                        },
                    }
                    await _send_client_json(websocket, id_usuario, error_payload)
                    continue

                websocket_cliente_enviado = await clients_ws_manager.send_to_user(
                    id_usuario_cliente,
                    {
                        "tipo": "ruta_proveedor",
                        "data": data,
                    },
                )
                logger.info(
                    "clients_mechanic_location_forwarded user=%s client_user=%s notified=%s payload=%s",
                    id_usuario,
                    id_usuario_cliente,
                    websocket_cliente_enviado,
                    data,
                )
                await _send_client_json(
                    websocket,
                    id_usuario,
                    {
                        "tipo": "ubicacion_mecanico_actualizada_resultado",
                        "data": {
                            "id_usuario_cliente": id_usuario_cliente,
                            "websocket_cliente_enviado": websocket_cliente_enviado,
                        },
                    },
                )
                continue

            if mensaje.get("tipo") == "admin_cancelo_servicio":
                data = mensaje.get("data") or {}
                id_asignacion = data.get("id_asignacion")
                id_invitacion = data.get("id_invitacion")
                id_solicitud = data.get("id_solicitud")

                try:
                    id_asignacion = int(id_asignacion)
                    id_invitacion = int(id_invitacion)
                    id_solicitud = int(id_solicitud)
                except (TypeError, ValueError):
                    await _send_client_json(
                        websocket,
                        id_usuario,
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "id_asignacion, id_invitacion e id_solicitud deben ser numeros",
                            },
                        },
                    )
                    continue

                asignacion = (
                    db.query(Asignacion)
                    .filter(
                        Asignacion.id_asignacion == id_asignacion,
                        Asignacion.id_solicitud == id_solicitud,
                    )
                    .first()
                )
                invitacion = (
                    db.query(Invitacion)
                    .filter(
                        Invitacion.id_invitacion == id_invitacion,
                        Invitacion.id_solicitud == id_solicitud,
                    )
                    .first()
                )
                solicitud = (
                    db.query(Solicitud)
                    .filter(Solicitud.id_solicitud == id_solicitud)
                    .first()
                )

                if not asignacion or not invitacion or not solicitud:
                    await _send_client_json(
                        websocket,
                        id_usuario,
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "Asignacion, invitacion o solicitud no encontrada",
                            },
                        },
                    )
                    continue

                try:
                    asignacion.estado = "cancelado"
                    invitacion.estado = "rechazada"
                    solicitud.estado = "pendiente"
                    db.commit()
                    db.refresh(asignacion)
                    db.refresh(invitacion)
                    db.refresh(solicitud)
                except SQLAlchemyError:
                    db.rollback()
                    logger.exception(
                        "admin_cancel_service_error user=%s id_asignacion=%s id_invitacion=%s id_solicitud=%s",
                        id_usuario,
                        id_asignacion,
                        id_invitacion,
                        id_solicitud,
                    )
                    await _send_client_json(
                        websocket,
                        id_usuario,
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "No se pudo cancelar el servicio",
                            },
                        },
                    )
                    continue

                resultado_payload = {
                    "tipo": "admin_cancelo_servicio_resultado",
                    "data": {
                        "id_asignacion": asignacion.id_asignacion,
                        "id_invitacion": invitacion.id_invitacion,
                        "id_solicitud": solicitud.id_solicitud,
                        "estado_asignacion": asignacion.estado,
                        "estado_invitacion": invitacion.estado,
                        "estado_solicitud": solicitud.estado,
                    },
                }
                vehiculo = solicitud.vehiculo
                cliente = vehiculo.cliente if vehiculo else None
                if cliente:
                    cliente_notificado = await clients_ws_manager.send_to_user(
                        cliente.id_usuario,
                        resultado_payload,
                    )
                    logger.info(
                        "service_cancel_client_notified user=%s notified=%s id_solicitud=%s",
                        cliente.id_usuario,
                        cliente_notificado,
                        solicitud.id_solicitud,
                    )

                await _send_client_json(websocket, id_usuario, resultado_payload)
                continue

            respuesta = procesar_respuesta_invitacion_cliente(db, id_usuario, mensaje)
            await _send_client_json(websocket, id_usuario, respuesta)

            if respuesta.get("tipo") in {"invitacion_aceptada", "invitacion_rechazada"}:
                respuesta_data = respuesta.get("data") or {}
                id_taller = respuesta_data.get("id_taller")
                id_invitacion = respuesta_data.get("id_invitacion")
                id_solicitud = respuesta_data.get("id_solicitud")

                if id_taller is not None:
                    taller = get_active_taller_by_id(db, int(id_taller))
                    if taller:
                        nombre_usuario = (
                            usuario.persona.nombre_completo
                            if usuario.persona and usuario.persona.nombre_completo
                            else usuario.email
                        )
                        accion = "acepto" if respuesta.get("tipo") == "invitacion_aceptada" else "rechazo"
                        admin_payload = {
                            "tipo": "respuesta_invitacion_cliente",
                            "data": {
                                "id_solicitud": id_solicitud,
                                "id_invitacion": id_invitacion,
                                "id_taller": int(id_taller),
                                "accion": accion,
                                "nombre_usuario": nombre_usuario,
                            },
                        }
                        admin_notificado = await clients_ws_manager.send_to_user(
                            taller.id_usuario,
                            admin_payload,
                        )
                        logger.info(
                            "clients_admin_notified user=%s event=%s notified=%s id_invitacion=%s",
                            taller.id_usuario,
                            admin_payload["tipo"],
                            admin_notificado,
                            id_invitacion,
                        )
    except (HTTPException, JWTError, TypeError, ValueError):
        logger.exception("clients_connection_closed_by_error user=%s", id_usuario)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    except WebSocketDisconnect:
        logger.info("clients_connection_closed user=%s", id_usuario)
    finally:
        db.close()
        if id_usuario is not None:
            clients_ws_manager.disconnect(id_usuario, websocket)


@router.websocket("/ws/proveedor")
async def websocket_provider(websocket: WebSocket, token: str):
    db = SessionLocal()
    id_usuario: int | None = None

    try:
        payload = verify_token(token)
        id_usuario = int(payload.get("sub"))
        usuario = db.query(User).filter(User.id_usuario == id_usuario, User.activo.is_(True)).first()
        if not usuario:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        provider_assignments = list_active_provider_assignments_by_user(db, id_usuario)
        owned_talleres = list_talleres_by_usuario(db, id_usuario)
        allowed_taller_ids = {
            assignment.id_taller for assignment in provider_assignments
        } | {
            taller.id_taller for taller in owned_talleres if taller.activo
        }

        await providers_ws_manager.connect(id_usuario, websocket)
        logger.info(
            "connection_open user=%s total_empresas=%s total_talleres_propios=%s talleres=%s",
            id_usuario,
            len(provider_assignments),
            len(owned_talleres),
            sorted(allowed_taller_ids),
        )
        await _send_provider_json(
            websocket,
            id_usuario,
            {
                "tipo": "conexion_proveedor_ok",
                "data": {
                    "id_usuario": id_usuario,
                    "total_empresas": len(provider_assignments),
                    "total_talleres_propios": len(owned_talleres),
                },
            },
        )

        while True:
            mensaje = await websocket.receive_json()
            tipo = mensaje.get("tipo")
            logger.info("message_received user=%s tipo=%s payload=%s", id_usuario, tipo, mensaje)

            if tipo == "ping":
                await _send_provider_json(
                    websocket,
                    id_usuario,
                    {
                        "tipo": "pong",
                        "data": {
                            "mensaje": "conexion activa",
                            "id_usuario": id_usuario,
                        },
                    },
                )
                continue

            if tipo == "obtener_perfil_proveedor":
                perfil_payload = {
                    "tipo": "perfil_proveedor",
                    "data": get_current_provider_profile(db, usuario),
                }
                await _send_provider_json(websocket, id_usuario, perfil_payload)
                continue

            if tipo == "recorriendo":
                data = mensaje.get("data") or {}
                id_asignacion = data.get("id_asignacion")
                latitud = data.get("latitud")
                longitud = data.get("longitud")

                try:
                    id_asignacion = int(id_asignacion)
                    latitud = float(latitud)
                    longitud = float(longitud)
                except (TypeError, ValueError):
                    logger.warning(
                        "validation_error user=%s tipo=%s payload=%s",
                        id_usuario,
                        tipo,
                        mensaje,
                    )
                    await _send_provider_json(
                        websocket,
                        id_usuario,
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "id_asignacion, latitud y longitud deben ser numeros",
                            },
                        },
                    )
                    continue

                asignacion = get_asignacion_with_solicitud_by_id(db, id_asignacion)
                solicitud = asignacion.solicitud if asignacion else None
                vehiculo = solicitud.vehiculo if solicitud else None
                cliente = vehiculo.cliente if vehiculo else None

                if not asignacion or not solicitud or not cliente:
                    logger.warning(
                        "invalid_route_update user=%s id_asignacion=%s",
                        id_usuario,
                        id_asignacion,
                    )
                    await _send_provider_json(
                        websocket,
                        id_usuario,
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "Asignacion o cliente no encontrado",
                            },
                        },
                    )
                    continue

                proveedor_actual = get_active_provider_assignment_by_user_and_taller(
                    db,
                    id_usuario,
                    asignacion.id_taller,
                )
                if (
                    not proveedor_actual
                    or asignacion.id_proveedor != proveedor_actual.id_proveedor
                ):
                    logger.warning(
                        "route_update_forbidden user=%s id_asignacion=%s id_taller=%s",
                        id_usuario,
                        id_asignacion,
                        asignacion.id_taller,
                    )
                    await _send_provider_json(
                        websocket,
                        id_usuario,
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "La asignacion no pertenece al proveedor autenticado",
                            },
                        },
                    )
                    continue

                cliente_payload = {
                    "tipo": "proveedor_recorrido",
                    "data": {
                        "id_asignacion": asignacion.id_asignacion,
                        "id_solicitud": solicitud.id_solicitud,
                        "latitud": latitud,
                        "longitud": longitud,
                    },
                }
                websocket_cliente_enviado = await clients_ws_manager.send_to_user(
                    cliente.id_usuario,
                    cliente_payload,
                )
                logger.info(
                    "provider_route_forwarded user=%s client_user=%s notified=%s id_asignacion=%s id_solicitud=%s",
                    id_usuario,
                    cliente.id_usuario,
                    websocket_cliente_enviado,
                    asignacion.id_asignacion,
                    solicitud.id_solicitud,
                )
                continue

            if tipo == "solicitud_aceptada":
                data = mensaje.get("data") or {}
                id_solicitud = data.get("id_solicitud")
                id_invitacion = data.get("id_invitacion")
                id_taller = data.get("id_taller")

                try:
                    id_solicitud = int(id_solicitud)
                    id_invitacion = int(id_invitacion)
                    id_taller = int(id_taller)
                except (TypeError, ValueError):
                    logger.warning(
                        "validation_error user=%s tipo=%s payload=%s",
                        id_usuario,
                        tipo,
                        mensaje,
                    )
                    await _send_provider_json(
                        websocket,
                        id_usuario,
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "id_solicitud, id_invitacion e id_taller deben ser numeros",
                            },
                        },
                    )
                    continue

                if id_taller not in allowed_taller_ids:
                    logger.warning(
                        "forbidden_taller user=%s id_taller=%s allowed_taller_ids=%s",
                        id_usuario,
                        id_taller,
                        sorted(allowed_taller_ids),
                    )
                    await _send_provider_json(
                        websocket,
                        id_usuario,
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "No tienes acceso al taller indicado",
                            },
                        },
                    )
                    continue

                proveedor_actual = get_active_provider_assignment_by_user_and_taller(
                    db,
                    id_usuario,
                    id_taller,
                )
                if not proveedor_actual:
                    logger.warning(
                        "provider_not_found_for_user user=%s id_taller=%s",
                        id_usuario,
                        id_taller,
                    )
                    await _send_provider_json(
                        websocket,
                        id_usuario,
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "No existe proveedor activo para el usuario autenticado en el taller",
                            },
                        },
                    )
                    continue

                solicitud = (
                    db.query(Solicitud)
                    .filter(Solicitud.id_solicitud == id_solicitud)
                    .first()
                )
                invitacion = (
                    db.query(Invitacion)
                    .filter(
                        Invitacion.id_invitacion == id_invitacion,
                        Invitacion.id_solicitud == id_solicitud,
                        Invitacion.id_taller == id_taller,
                    )
                    .first()
                )
                if not solicitud or not invitacion:
                    logger.warning(
                        "invalid_request_acceptance user=%s id_solicitud=%s id_invitacion=%s id_taller=%s",
                        id_usuario,
                        id_solicitud,
                        id_invitacion,
                        id_taller,
                    )
                    await _send_provider_json(
                        websocket,
                        id_usuario,
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "Solicitud o invitacion no encontrada para el taller indicado",
                            },
                        },
                    )
                    continue

                try:
                    asignacion = Asignacion(
                        id_solicitud=id_solicitud,
                        id_taller=id_taller,
                        id_proveedor=proveedor_actual.id_proveedor,
                        fecha_inicio=datetime.now(),
                        fecha_fin=None,
                        tiempo_llegada=None,
                        estado="asignada",
                    )
                    solicitud.estado = "asignada"
                    invitacion.estado = "aceptada"
                    invitacion.fecha_hora_respuesta = datetime.now()
                    proveedor_actual.estado = "Ocupado"
                    (
                        db.query(Invitacion)
                        .filter(
                            Invitacion.id_solicitud == id_solicitud,
                            Invitacion.id_invitacion != id_invitacion,
                            Invitacion.estado != "expirada",
                        )
                        .update(
                            {Invitacion.estado: "cerrada"},
                            synchronize_session=False,
                        )
                    )
                    db.add(asignacion)
                    db.commit()
                    db.refresh(asignacion)
                    db.refresh(solicitud)
                    db.refresh(invitacion)
                    db.refresh(proveedor_actual)
                except SQLAlchemyError:
                    db.rollback()
                    logger.exception(
                        "solicitud_aceptada_error user=%s id_solicitud=%s id_invitacion=%s id_taller=%s",
                        id_usuario,
                        id_solicitud,
                        id_invitacion,
                        id_taller,
                    )
                    await _send_provider_json(
                        websocket,
                        id_usuario,
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "No se pudo aceptar la solicitud",
                            },
                        },
                    )
                    continue

                await notificar_solicitud_asignada_a_cliente(solicitud)

                resultado_payload = {
                    "tipo": "solicitud_aceptada_resultado",
                    "data": {
                        "id_asignacion": asignacion.id_asignacion,
                        "id_solicitud": solicitud.id_solicitud,
                        "id_invitacion": invitacion.id_invitacion,
                        "id_taller": asignacion.id_taller,
                        "id_proveedor": asignacion.id_proveedor,
                        "estado_asignacion": asignacion.estado,
                        "estado_solicitud": solicitud.estado,
                        "estado_invitacion": invitacion.estado,
                        "fecha_inicio": asignacion.fecha_inicio.isoformat()
                        if asignacion.fecha_inicio
                        else None,
                    },
                }
                usuarios_notificados = await notificar_solicitud_aceptada_a_proveedores_taller(
                    db,
                    asignacion.id_taller,
                    resultado_payload,
                )
                logger.info(
                    "solicitud_accepted_by_provider user=%s id_asignacion=%s id_solicitud=%s id_invitacion=%s id_taller=%s id_proveedor=%s proveedores_notificados=%s",
                    id_usuario,
                    asignacion.id_asignacion,
                    solicitud.id_solicitud,
                    invitacion.id_invitacion,
                    asignacion.id_taller,
                    asignacion.id_proveedor,
                    usuarios_notificados,
                )
                continue

            if tipo in {"proveedor_acepto", "proveedor_rechazo"}:
                data = mensaje.get("data") or {}
                id_asignacion = data.get("id_asignacion")
                id_taller = data.get("id_taller")

                try:
                    id_asignacion = int(id_asignacion)
                    id_taller = int(id_taller)
                except (TypeError, ValueError):
                    logger.warning(
                        "validation_error user=%s tipo=%s payload=%s",
                        id_usuario,
                        tipo,
                        mensaje,
                    )
                    await _send_provider_json(
                        websocket,
                        id_usuario,
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "id_asignacion e id_taller deben ser numeros",
                            },
                        },
                    )
                    continue

                if id_taller not in allowed_taller_ids:
                    logger.warning(
                        "forbidden_taller user=%s id_taller=%s allowed_taller_ids=%s",
                        id_usuario,
                        id_taller,
                        sorted(allowed_taller_ids),
                    )
                    await _send_provider_json(
                        websocket,
                        id_usuario,
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "No tienes acceso al taller indicado",
                            },
                        },
                    )
                    continue

                proveedor_actual = get_active_provider_assignment_by_user_and_taller(
                    db,
                    id_usuario,
                    id_taller,
                )
                if not proveedor_actual:
                    logger.warning(
                        "provider_not_found_for_user user=%s id_taller=%s",
                        id_usuario,
                        id_taller,
                    )
                    await _send_provider_json(
                        websocket,
                        id_usuario,
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "No existe proveedor activo para el usuario autenticado en el taller",
                            },
                        },
                    )
                    continue

                asignacion = get_asignacion_with_solicitud_by_id(db, id_asignacion)
                if not asignacion or asignacion.id_taller != id_taller:
                    logger.warning(
                        "invalid_assignment user=%s id_asignacion=%s id_taller=%s",
                        id_usuario,
                        id_asignacion,
                        id_taller,
                    )
                    await _send_provider_json(
                        websocket,
                        id_usuario,
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "La asignacion no existe para el taller indicado",
                            },
                        },
                    )
                    continue

                servicio_creado = None
                try:
                    if tipo == "proveedor_acepto":
                        asignacion.id_proveedor = proveedor_actual.id_proveedor
                        asignacion.estado = "Asignado"
                        proveedor_actual.estado = "Ocupado"
                        servicio_creado = Servicio(
                            id_asignacion=asignacion.id_asignacion,
                            id_pago=None,
                            total=Decimal("0.00"),
                            fecha_inicio=datetime.now(),
                            fecha_fin=None,
                            estado="En curso",
                        )
                        db.add(servicio_creado)
                    else:
                        asignacion.id_proveedor = None
                        asignacion.estado = "Pendiente de asignar personal"

                    db.commit()
                    db.refresh(asignacion)
                    db.refresh(proveedor_actual)
                    if servicio_creado:
                        db.refresh(servicio_creado)
                except SQLAlchemyError:
                    db.rollback()
                    logger.exception(
                        "assignment_update_error user=%s tipo=%s id_asignacion=%s",
                        id_usuario,
                        tipo,
                        id_asignacion,
                    )
                    await _send_provider_json(
                        websocket,
                        id_usuario,
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "No se pudo actualizar la asignacion",
                            },
                        },
                    )
                    continue

                if tipo == "proveedor_rechazo":
                    taller = get_active_taller_by_id(db, id_taller)
                    if taller:
                        admin_payload = {
                            "tipo": "asignacion_rechazada",
                            "data": {
                                "id_asignacion": asignacion.id_asignacion,
                                "id_taller": asignacion.id_taller,
                                "asignada": False,
                            },
                        }
                        admin_notificado = await providers_ws_manager.send_to_user(
                            taller.id_usuario,
                            admin_payload,
                        )
                        logger.info(
                            "admin_notified user=%s event=%s notified=%s id_asignacion=%s",
                            taller.id_usuario,
                            admin_payload["tipo"],
                            admin_notificado,
                            asignacion.id_asignacion,
                        )

                solicitud = asignacion.solicitud
                vehiculo = solicitud.vehiculo if solicitud else None
                cliente = vehiculo.cliente if vehiculo else None

                if tipo == "proveedor_acepto":
                    taller = get_active_taller_by_id(db, id_taller)
                    if taller:
                        admin_payload = {
                            "tipo": "proveedor_acepto_resultado",
                            "data": {
                                "id_asignacion": asignacion.id_asignacion,
                                "id_usuario_cliente": cliente.id_usuario if cliente else None,
                                "estado_asignacion": asignacion.estado,
                                "id_servicio": servicio_creado.id_servicio if servicio_creado else None,
                            },
                        }
                        admin_notificado = await providers_ws_manager.send_to_user(
                            taller.id_usuario,
                            admin_payload,
                        )
                        logger.info(
                            "admin_notified user=%s event=%s notified=%s id_asignacion=%s id_servicio=%s",
                            taller.id_usuario,
                            admin_payload["tipo"],
                            admin_notificado,
                            asignacion.id_asignacion,
                            servicio_creado.id_servicio if servicio_creado else None,
                        )

                tipo_resultado = f"{tipo}_resultado"
                await _send_provider_json(
                    websocket,
                    id_usuario,
                    {
                        "tipo": tipo_resultado,
                        "data": {
                            "id_asignacion": asignacion.id_asignacion,
                            "id_taller": asignacion.id_taller,
                            "id_personal": id_usuario,
                            "id_proveedor": asignacion.id_proveedor,
                            "estado_asignacion": asignacion.estado,
                            "estado_proveedor": proveedor_actual.estado,
                            "id_servicio": servicio_creado.id_servicio if servicio_creado else None,
                            "id_usuario_cliente": cliente.id_usuario if cliente else None,
                        },
                    },
                )
                logger.info(
                    "assignment_updated_by_provider user=%s tipo=%s id_asignacion=%s id_proveedor=%s estado=%s estado_proveedor=%s",
                    id_usuario,
                    tipo,
                    asignacion.id_asignacion,
                    asignacion.id_proveedor,
                    asignacion.estado,
                    proveedor_actual.estado,
                )
                continue

            if tipo == "aceptar_asignacion":
                data = mensaje.get("data") or {}
                id_asignacion = data.get("id_asignacion")
                id_personal = data.get("id_personal")
                id_taller = data.get("id_taller")

                try:
                    id_asignacion = int(id_asignacion)
                    id_personal = int(id_personal)
                    id_taller = int(id_taller)
                except (TypeError, ValueError):
                    logger.warning(
                        "validation_error user=%s tipo=%s payload=%s",
                        id_usuario,
                        tipo,
                        mensaje,
                    )
                    await _send_provider_json(
                        websocket,
                        id_usuario,
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "id_asignacion, id_personal e id_taller deben ser numeros",
                            },
                        },
                    )
                    continue

                if id_taller not in allowed_taller_ids:
                    logger.warning(
                        "forbidden_taller user=%s id_taller=%s allowed_taller_ids=%s",
                        id_usuario,
                        id_taller,
                        sorted(allowed_taller_ids),
                    )
                    await _send_provider_json(
                        websocket,
                        id_usuario,
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "No tienes acceso al taller indicado",
                            },
                        },
                    )
                    continue

                provider_target = get_active_provider_assignment_by_user_and_taller(
                    db,
                    id_personal,
                    id_taller,
                )
                if not provider_target:
                    logger.warning(
                        "invalid_target user=%s id_personal=%s id_taller=%s",
                        id_usuario,
                        id_personal,
                        id_taller,
                    )
                    await _send_provider_json(
                        websocket,
                        id_usuario,
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "El id_personal no pertenece al taller o no esta activo",
                            },
                        },
                    )
                    continue

                asignacion = get_asignacion_with_solicitud_by_id(db, id_asignacion)
                if not asignacion or asignacion.id_taller != id_taller:
                    logger.warning(
                        "invalid_assignment user=%s id_asignacion=%s id_taller=%s",
                        id_usuario,
                        id_asignacion,
                        id_taller,
                    )
                    await _send_provider_json(
                        websocket,
                        id_usuario,
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "La asignacion no existe para el taller indicado",
                            },
                        },
                    )
                    continue

                try:
                    asignacion.id_proveedor = provider_target.id_proveedor
                    asignacion.estado = "enviada"
                    db.commit()
                    db.refresh(asignacion)
                except SQLAlchemyError:
                    db.rollback()
                    logger.exception(
                        "assignment_update_error user=%s tipo=%s id_asignacion=%s",
                        id_usuario,
                        tipo,
                        id_asignacion,
                    )
                    await _send_provider_json(
                        websocket,
                        id_usuario,
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "No se pudo actualizar el estado de la asignacion",
                            },
                        },
                    )
                    continue

                solicitud = asignacion.solicitud
                vehiculo = solicitud.vehiculo if solicitud else None
                nombre_vehiculo = None
                if vehiculo:
                    nombre_vehiculo = f"{vehiculo.marca} {vehiculo.modelo}".strip()

                solicitud_payload = {
                    "id_solicitud": solicitud.id_solicitud,
                    "id_vehiculo": solicitud.id_vehiculo,
                    "nombre_vehiculo": nombre_vehiculo,
                    "descripcion": solicitud.descripcion,
                    "latitud": solicitud.latitud,
                    "direccion": solicitud.direccion,
                    "longitud": solicitud.longitud,
                    "fecha": solicitud.fecha.isoformat() if solicitud.fecha else None,
                    "prioridad": solicitud.prioridad,
                    "observaciones": solicitud.observaciones,
                    "audio": solicitud.audio,
                    "imagenes": solicitud.imagenes,
                    "estado": solicitud.estado,
                }

                payload_personal = {
                    "tipo": "asignacion_aceptada",
                    "data": {
                        "id_asignacion": asignacion.id_asignacion,
                        "id_taller": asignacion.id_taller,
                        "id_personal": id_personal,
                        "id_solicitud": solicitud.id_solicitud,
                        "id_vehiculo": solicitud.id_vehiculo,
                    },
                }
                websocket_enviado = await providers_ws_manager.send_to_user(
                    id_personal,
                    payload_personal,
                )
                logger.info(
                    "sent_to_user=%s event=%s websocket_enviado=%s id_asignacion=%s id_taller=%s",
                    id_personal,
                    payload_personal["tipo"],
                    websocket_enviado,
                    asignacion.id_asignacion,
                    asignacion.id_taller,
                )

                resultado_payload = {
                    "tipo": "aceptar_asignacion_resultado",
                    "data": {
                        "id_asignacion": asignacion.id_asignacion,
                        "id_taller": asignacion.id_taller,
                        "id_personal": id_personal,
                        "websocket_enviado": websocket_enviado,
                        "solicitud": solicitud_payload,
                    },
                }
                await _send_provider_json(websocket, id_usuario, resultado_payload)
                continue

            logger.warning("unsupported_type user=%s tipo=%s payload=%s", id_usuario, tipo, mensaje)
            await _send_provider_json(
                websocket,
                id_usuario,
                {
                    "tipo": "error",
                    "data": {
                        "mensaje": "Tipo de mensaje no soportado",
                        "tipos_permitidos": [
                            "ping",
                            "obtener_perfil_proveedor",
                            "recorriendo",
                            "solicitud_aceptada",
                            "aceptar_asignacion",
                            "proveedor_acepto",
                            "proveedor_rechazo",
                        ],
                    },
                },
            )
    except (HTTPException, JWTError, TypeError, ValueError):
        logger.exception("connection_closed_by_error user=%s", id_usuario)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    except WebSocketDisconnect:
        logger.info("connection_closed user=%s", id_usuario)
    finally:
        db.close()
        if id_usuario is not None:
            providers_ws_manager.disconnect(id_usuario, websocket)
