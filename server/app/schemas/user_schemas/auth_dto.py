from pydantic import BaseModel
from typing import Optional

class AuthRequestCode(BaseModel):
    """Шаг 1: Запрос OTP кода по номеру телефона в Telegram-бот"""
    phone_number: str

class AuthVerifyCode(BaseModel):
    """Шаг 2: Проверка кода и выдача токенов"""
    phone_number: str
    code: str
    remember_me: bool = False
    device_info: Optional[str] = None  # Например, "MAZ-WORKSTATION-402"

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"

class TokenRefreshRequest(BaseModel):
    refresh_token: str