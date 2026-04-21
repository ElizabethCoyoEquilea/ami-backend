from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from jose import JWTError

from app.core.database import SessionLocal
from app.core.security import verify_token
from app.models.usuarios.cliente import Cliente
from app.models.usuarios.usuario import User
from app.services.cotizaciones_service import procesar_respuesta_cotizacion_cliente
from app.websockets.connection_manager import clients_ws_manager


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
