from fastapi import WebSocket


class WebSocketConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[int, set[WebSocket]] = {}

    async def connect(self, id_usuario: int, websocket: WebSocket) -> None:
        await websocket.accept()
        conexiones = self.active_connections.setdefault(id_usuario, set())
        conexiones.add(websocket)

    def disconnect(self, id_usuario: int, websocket: WebSocket) -> None:
        conexiones = self.active_connections.get(id_usuario)
        if not conexiones:
            return

        conexiones.discard(websocket)
        if not conexiones:
            self.active_connections.pop(id_usuario, None)

    async def send_to_user(self, id_usuario: int, message: dict) -> bool:
        conexiones = self.active_connections.get(id_usuario)
        if not conexiones:
            return False

        enviado = False
        for websocket in list(conexiones):
            try:
                await websocket.send_json(message)
                enviado = True
            except RuntimeError:
                self.disconnect(id_usuario, websocket)

        return enviado


clients_ws_manager = WebSocketConnectionManager()
providers_ws_manager = WebSocketConnectionManager()
