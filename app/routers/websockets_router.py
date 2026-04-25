from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from jose import JWTError

from app.core.database import SessionLocal
from app.core.security import verify_token
from app.models.usuarios.cliente import Cliente
from app.models.usuarios.usuario import User
from app.repositories.talleres_repository import (
    get_active_provider_assignment_by_user_and_taller,
    get_asignacion_with_solicitud_by_id,
    list_active_provider_assignments_by_user,
)
from app.services.cotizaciones_service import procesar_respuesta_cotizacion_cliente
from app.services.usuarios_service import get_current_provider_profile
from app.websockets.connection_manager import clients_ws_manager, providers_ws_manager


router = APIRouter(tags=["WebSockets"])


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

        while True:
            mensaje = await websocket.receive_json()
            respuesta = procesar_respuesta_cotizacion_cliente(db, id_usuario, mensaje)
            await websocket.send_json(respuesta)
    except (HTTPException, JWTError, TypeError, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    except WebSocketDisconnect:
        pass
    finally:
        db.close()
        if id_usuario is not None:
            clients_ws_manager.disconnect(id_usuario)


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
        await websocket.send_json(
            {
                "tipo": "conexion_proveedor_ok",
                "data": {
                    "id_usuario": id_usuario,
                    "total_empresas": len(provider_assignments),
                },
            }
        )

        while True:
            mensaje = await websocket.receive_json()
            tipo = mensaje.get("tipo")

            if tipo == "ping":
                await websocket.send_json(
                    {
                        "tipo": "pong",
                        "data": {
                            "mensaje": "conexion activa",
                            "id_usuario": id_usuario,
                        },
                    }
                )
                continue

            if tipo == "obtener_perfil_proveedor":
                await websocket.send_json(
                    {
                        "tipo": "perfil_proveedor",
                        "data": get_current_provider_profile(db, usuario),
                    }
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
                    await websocket.send_json(
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "id_asignacion, id_personal e id_taller deben ser numeros",
                            },
                        }
                    )
                    continue

                if id_taller not in allowed_taller_ids:
                    await websocket.send_json(
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "No tienes acceso al taller indicado",
                            },
                        }
                    )
                    continue

                provider_target = get_active_provider_assignment_by_user_and_taller(
                    db,
                    id_personal,
                    id_taller,
                )
                if not provider_target:
                    await websocket.send_json(
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "El id_personal no pertenece al taller o no esta activo",
                            },
                        }
                    )
                    continue

                asignacion = get_asignacion_with_solicitud_by_id(db, id_asignacion)
                if not asignacion or asignacion.id_taller != id_taller:
                    await websocket.send_json(
                        {
                            "tipo": "error",
                            "data": {
                                "mensaje": "La asignacion no existe para el taller indicado",
                            },
                        }
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
                        "estado_asignacion": asignacion.estado,
                        "solicitud": solicitud_payload,
                    },
                }
                websocket_enviado = await providers_ws_manager.send_to_user(
                    id_personal,
                    payload_personal,
                )

                await websocket.send_json(
                    {
                        "tipo": "aceptar_asignacion_resultado",
                        "data": {
                            "id_asignacion": asignacion.id_asignacion,
                            "id_taller": asignacion.id_taller,
                            "id_personal": id_personal,
                            "websocket_enviado": websocket_enviado,
                            "solicitud": solicitud_payload,
                        },
                    }
                )
                continue

            await websocket.send_json(
                {
                    "tipo": "error",
                    "data": {
                        "mensaje": "Tipo de mensaje no soportado",
                        "tipos_permitidos": [
                            "ping",
                            "obtener_perfil_proveedor",
                            "aceptar_asignacion",
                        ],
                    },
                }
            )
    except (HTTPException, JWTError, TypeError, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    except WebSocketDisconnect:
        pass
    finally:
        db.close()
        if id_usuario is not None:
            providers_ws_manager.disconnect(id_usuario)
