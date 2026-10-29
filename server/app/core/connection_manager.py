from fastapi import WebSocket
import logging

logger = logging.getLogger("app.websockets")

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[int, WebSocket] = {}

    async def connect(self, employee_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[employee_id] = websocket
        logger.info(f"WebSocket connected for employee_id={employee_id}")

    def disconnect(self, employee_id: int):
        if employee_id in self.active_connections:
            del self.active_connections[employee_id]
            logger.info(f"WebSocket disconnected for employee_id={employee_id}")

    async def send_personal_message(self, employee_id: int, message: dict):
        """Отправить сообщение конкретному пользователю и залогировать результат"""
        connection = self.active_connections.get(employee_id)
        if not connection:
            logger.info(f"WS message NOT sent: employee_id={employee_id} is offline (no active connection)")
            return False

        try:
            await connection.send_json(message)
            # Вот здесь сервер знает, что данные успешно улетели по сокету!
            logger.info(f"WS message successfully sent to employee_id={employee_id}: {message}")
            return True
        except Exception as e:
            logger.exception(f"Failed to send WS message to employee_id={employee_id}: {e}")
            self.disconnect(employee_id)
            return False

manager = ConnectionManager()