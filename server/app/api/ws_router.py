import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, status

from server.app.config import JWT_SECRET_KEY, JWT_ALGORITHM
from server.app.core.connection_manager import manager
from server.app.core.security_tokens import decode_access_token, \
    decode_access_token_ws  # Ваша функция декодирования токена

router = APIRouter(prefix="/ws", tags=["WebSockets"])


@router.websocket("/notifications")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(..., description="JWT токен авторизации клиента")
):
    """
    Эндпоинт для постоянного WebSocket-соединения с PyQt6 клиентом.
    Токен передается в query-параметрах при подключении.
    """
    # 1. Валидируем токен при подключении с помощью мягкой функции
    payload = decode_access_token_ws(token)
    if not payload:
        # Корректно закрываем сокет по спецификации WebSocket (Policy Violation)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        employee_id = int(payload.get("sub"))
    except (ValueError, TypeError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Регистрируем соединение
    await manager.connect(employee_id, websocket)
    try:
        while True:
            # Держим соединение открытым, ждем сообщения/пинги от клиента
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(employee_id)