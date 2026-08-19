import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator

def clean_and_normalize_phone(v: str) -> str:
    """Унифицирует телефонные номера под формат +375XXXXXXXXX (Беларусь)"""
    digits = "".join(re.findall(r"\d", v))

    if digits.startswith("80") and len(digits) == 11:
        digits = "375" + digits[2:]
    elif len(digits) == 9 and (
        digits.startswith("29") or digits.startswith("44") or
        digits.startswith("33") or digits.startswith("25")
    ):
        digits = "375" + digits

    if not digits.startswith("375") or len(digits) != 12:
        raise ValueError(
            "Номер телефона должен быть в международном формате (например, +375XXXXXXXXX)"
        )
    return f"+{digits}"


class UserLoginRequest(BaseModel):
    """Схема для входа по номеру телефона и паролю"""
    phone_number: str = Field(..., description="Номер телефона пользователя")
    password: str = Field(..., description="Пароль, полученный через Telegram")
    remember_me: bool = Field(False, description="Флаг 'Запомнить меня'")
    device_info: Optional[str] = Field(None, description="Информация об устройстве для истории сессий")

    @field_validator("phone_number")
    @classmethod
    def normalize_phone_number(cls, v: str) -> str:
        return clean_and_normalize_phone(v)


class TokenResponse(BaseModel):
    """Ответ с токенами при успешном входе или обновлении"""
    access_token: str = Field(..., description="JWT access токен")
    refresh_token: Optional[str] = Field(None, description="Сессионный refresh токен")
    token_type: str = Field("bearer", description="Тип токена")


class TokenRefreshRequest(BaseModel):
    """Запрос на обновление access токена по refresh-токену"""
    refresh_token: str = Field(..., description="Действующий refresh токен")


class PasswordChangeRequest(BaseModel):
    old_password: str = Field(..., description="Текущий пароль")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=64,
        description="Новый надежный пароль (8-64 символа, заглавные/строчные буквы, цифры)",
    )

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        # 1. Проверка наличия хотя бы одной заглавной буквы
        if not re.search(r"[A-ZА-ЯЁ]", value):
            raise ValueError(
                "Пароль должен содержать хотя бы одну заглавную букву (латиница или кириллица)."
            )

        # 2. Проверка наличия хотя бы одной строчной буквы
        if not re.search(r"[a-zа-яё]", value):
            raise ValueError(
                "Пароль должен содержать хотя бы одну строчную букву."
            )

        # 3. Проверка наличия хотя бы одной цифры
        if not re.search(r"\d", value):
            raise ValueError("Пароль должен содержать хотя бы одну цифру.")

        # 4. (Опционально) Проверка наличия спецсимволов
        # if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?]", value):
        #     raise ValueError("Пароль должен содержать хотя бы один спецсимвол.")

        return value


class ForgotPasswordRequest(BaseModel):
    phone_number: str

    @field_validator("phone_number")
    @classmethod
    def normalize(cls, v: str) -> str:
        return clean_and_normalize_phone(v)

class ResetPasswordConfirm(BaseModel):
    phone_number: str
    code: str = Field(..., min_length=4, max_length=8)
    new_password: str = Field(..., min_length=6)

    @field_validator("phone_number")
    @classmethod
    def normalize(cls, v: str) -> str:
        return clean_and_normalize_phone(v)


class VerifyResetCodeRequest(BaseModel):
    phone_number: str = Field(..., description="Номер телефона сотрудника")
    code: str = Field(..., description="6-значный код из Telegram")