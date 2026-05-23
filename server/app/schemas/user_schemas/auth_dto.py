# --- СХЕМЫ АВТОРИЗАЦИИ (DTO) ---
from pydantic import BaseModel
from typing import Optional


class AuthRequestCode(BaseModel):
    """Шаг 1: Запрос кода по номеру телефона"""
    phone_number: str

class AuthVerifyCode(BaseModel):
    """Шаг 2: Проверка кода из Telegram"""
    phone_number: str
    code: str
    remember_me: bool = False
    device_info: Optional[str] = None  # Имя ПК, например "WORK-PC-01"

class TokenResponse(BaseModel):
    """Ответ сервера при успешном входе"""
    access_token: str
    refresh_token: Optional[str] = None  # Выдается, только если была галочка "Запомнить меня"
    token_type: str = "bearer"

class TokenRefreshRequest(BaseModel):
    """Шаг 3: Автоматический вход по токену обновления"""
    refresh_token: str