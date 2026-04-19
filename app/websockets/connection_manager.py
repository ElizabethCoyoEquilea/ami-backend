from fastapi import WebSocket


class WebSocketConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, id_usuario: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections[id_usuario] = websocket

    def disconnect(self, id_usuario: int) -> None:
        self.active_connections.pop(id_usuario, None)

    async def send_to_user(self, id_usuario: int, message: dict) -> bool:
        websocket = self.active_connections.get(id_usuario)
        if not websocket:
            return False

        try:
            await websocket.send_json(message)
            return True
        except RuntimeError:
            self.disconnect(id_usuario)
            return False


clients_ws_manager = WebSocketConnectionManager()
