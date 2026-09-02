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


def validate_password_strength_func(value: str) -> str:
    """Общая логика проверки сложности пароля"""
    if not re.search(r"[A-ZА-ЯЁ]", value):
        raise ValueError("Пароль должен содержать хотя бы одну заглавную букву.")
    if not re.search(r"[a-zа-яё]", value):
        raise ValueError("Пароль должен содержать хотя бы одну строчную букву.")
    if not re.search(r"\d", value):
        raise ValueError("Пароль должен содержать хотя бы одну цифру.")
    return value


class UserLoginRequest(BaseModel):
    """Схема для входа по номеру телефона и паролю"""
    phone_number: str = Field(..., description="Номер телефона пользователя", examples=["+375291234567"])
    password: str = Field(..., description="Пароль, полученный через Telegram", examples=["SecretPass123"])
    remember_me: bool = Field(False, description="Флаг 'Запомнить меня'")
    device_info: str = Field(None, description="Информация об устройстве для истории сессий", examples=["Desktop Windows"])

    @field_validator("phone_number")
    @classmethod
    def normalize_phone_number(cls, v: str) -> str:
        return clean_and_normalize_phone(v)


class TokenResponse(BaseModel):
    """Ответ с токенами при успешном входе или обновлении"""
    access_token: str = Field(..., description="JWT access токен", examples=["eyJhbGciOiJIUzI1NiI..."])
    refresh_token: Optional[str] = Field(None, description="Сессионный refresh токен", examples=["d9b2d63d-a232-4328..."])
    token_type: str = Field("bearer", description="Тип токена", examples=["bearer"])


class TokenRefreshRequest(BaseModel):
    """Запрос на обновление access токена по refresh-токену"""
    refresh_token: str = Field(..., description="Действующий refresh токен", examples=["d9b2d63d-a232-4328..."])


class PasswordChangeRequest(BaseModel):
    old_password: str = Field(..., description="Текущий пароль", examples=["OldPassword123"])
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=64,
        description="Новый надежный пароль (8-64 символа, заглавные/строчные буквы, цифры)",
        examples=["NewPassword123"]
    )

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        return validate_password_strength_func(value)


class ForgotPasswordRequest(BaseModel):
    phone_number: str = Field(..., description="Номер телефона", examples=["+375291234567"])

    @field_validator("phone_number")
    @classmethod
    def normalize(cls, v: str) -> str:
        return clean_and_normalize_phone(v)


class VerifyResetCodeRequest(BaseModel):
    phone_number: str = Field(..., description="Номер телефона сотрудника", examples=["+375291234567"])
    code: str = Field(..., description="6-значный код из Telegram", examples=["123456"])

    @field_validator("phone_number")
    @classmethod
    def normalize(cls, v: str) -> str:
        return clean_and_normalize_phone(v)


class ResetPasswordConfirm(BaseModel):
    phone_number: str = Field(..., description="Номер телефона", examples=["+375291234567"])
    code: str = Field(..., min_length=4, max_length=8, description="Код из Telegram", examples=["123456"])
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=64,
        description="Новый пароль (8-64 символа)",
        examples=["BrandNewPass123"]
    )

    @field_validator("phone_number")
    @classmethod
    def normalize(cls, v: str) -> str:
        return clean_and_normalize_phone(v)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        return validate_password_strength_func(value)