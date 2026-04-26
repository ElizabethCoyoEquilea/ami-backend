import logging
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from jose import JWTError
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import SessionLocal
from app.core.security import verify_token
from app.models.solicitudes.servicio import Servicio
from app.models.usuarios.cliente import Cliente
from app.models.usuarios.usuario import User
from app.repositories.talleres_repository import (
    get_active_provider_assignment_by_user_and_taller,
    get_active_taller_by_id,
    get_asignacion_with_solicitud_by_id,
    list_active_provider_assignments_by_user,
)
from app.services.cotizaciones_service import (
    procesar_respuesta_cotizacion_cliente,
    registrar_cotizacion_pendiente,
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
            .join(Cliente, Cliente.id_usuario == User.id_usuario)
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
                    cotizacion = registrar_cotizacion_pendiente(
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
                        "tipo": "nueva_cotizacion",
                        "data": {
                            "id_solicitud": cotizacion.id_solicitud,
                            "id_taller": cotizacion.id_taller,
                            "id_cotizacion": cotizacion.id_cotizacion,
                            "estado_cotizacion": cotizacion.estado,
                        },
                    }
                    admin_notificado = await clients_ws_manager.send_to_user(
                        taller.id_usuario,
                        admin_payload,
                    )
                    logger.info(
                        "clients_new_cotizacion_admin_notified user=%s event=%s notified=%s id_cotizacion=%s",
                        taller.id_usuario,
                        admin_payload["tipo"],
                        admin_notificado,
                        cotizacion.id_cotizacion,
                    )

                resultado_payload = {
                    "tipo": "cotizacion_creada",
                    "data": {
                        "id_cotizacion": cotizacion.id_cotizacion,
                        "id_solicitud": cotizacion.id_solicitud,
                        "id_taller": cotizacion.id_taller,
                        "monto": float(cotizacion.monto),
                        "estado": cotizacion.estado,
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

            respuesta = procesar_respuesta_cotizacion_cliente(db, id_usuario, mensaje)
            await _send_client_json(websocket, id_usuario, respuesta)

            if respuesta.get("tipo") in {"cotizacion_aceptada", "cotizacion_rechazada"}:
                respuesta_data = respuesta.get("data") or {}
                id_taller = respuesta_data.get("id_taller")
                id_cotizacion = respuesta_data.get("id_cotizacion")
                id_solicitud = respuesta_data.get("id_solicitud")

                if id_taller is not None:
                    taller = get_active_taller_by_id(db, int(id_taller))
                    if taller:
                        nombre_usuario = (
                            usuario.persona.nombre_completo
                            if usuario.persona and usuario.persona.nombre_completo
                            else usuario.email
                        )
                        accion = "acepto" if respuesta.get("tipo") == "cotizacion_aceptada" else "rechazo"
                        admin_payload = {
                            "tipo": "respuesta_cotizacion_cliente",
                            "data": {
                                "id_solicitud": id_solicitud,
                                "id_cotizacion": id_cotizacion,
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
                            "clients_admin_notified user=%s event=%s notified=%s id_cotizacion=%s",
                            taller.id_usuario,
                            admin_payload["tipo"],
                            admin_notificado,
                            id_cotizacion,
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
        if not provider_assignments:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        allowed_taller_ids = {assignment.id_taller for assignment in provider_assignments}

        await providers_ws_manager.connect(id_usuario, websocket)
        logger.info(
            "connection_open user=%s total_empresas=%s talleres=%s",
            id_usuario,
            len(provider_assignments),
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
