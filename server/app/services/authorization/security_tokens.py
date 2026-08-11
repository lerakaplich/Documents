from datetime import datetime, timedelta, timezone
import jwt
from fastapi import HTTPException, status

from server.app.config import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_SECRET_KEY, JWT_ALGORITHM


def create_access_token(employee_id: int, role: str) -> str:
    """Генерирует стандартный подписанный JWT Access Токен"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(employee_id),
        "role": role,
        "exp": expire
    }
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str) -> dict:
    """
    Проверяет валидность JWT токена.
    Возвращает декодированный payload или кидает 401 ошибку.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Срок действия токена доступа истек."
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный токен доступа."
        )