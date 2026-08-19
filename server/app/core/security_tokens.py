import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import bcrypt
import jwt
from fastapi import HTTPException, status

from server.app.config import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_SECRET_KEY, JWT_ALGORITHM

logger = logging.getLogger("app.security")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Безопасная проверка хэша пароля."""
    if not hashed_password:
        return False
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(employee_id: int, service_number: str, is_leader: bool) -> str:
    """Генерирует единый стандартный подписанный JWT Access Токен."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(employee_id),
        "service_number": service_number,
        "is_leader": is_leader,
        "exp": expire
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Декодирует и проверяет валидность JWT токена.
    Возвращает payload или кидает HTTPException(401).
    """
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        logger.warning(
            "Access token verification failed: Token expired",
            extra={"event_type": "jwt_expired"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Срок действия access-токена истек. Обновите его через /auth/refresh",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.PyJWTError, ValueError) as exc:
        logger.warning(
            f"Access token verification failed: Invalid token ({type(exc).__name__})",
            extra={"event_type": "jwt_invalid"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный или искаженный сессионный токен.",
            headers={"WWW-Authenticate": "Bearer"},
        )

def hash_refresh_token(token: str) -> str:
    """Хеширует refresh-токен перед сохранением в БД."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()