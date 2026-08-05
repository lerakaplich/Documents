from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, websocket: WebSocket, employee_id: int):
        await websocket.accept()
        self.active_connections[employee_id] = websocket

    def disconnect(self, employee_id: int):
        if employee_id in self.active_connections:
            del self.active_connections[employee_id]

    async def send_personal_message(self, message: dict, employee_id: int):
        if employee_id in self.active_connections:
            await self.active_connections[employee_id].send_json(message)

manager = ConnectionManager()