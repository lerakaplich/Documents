import secrets
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from server.app.database.document_models import UserSession
from server.app.database.employee_models import Employee
from server.app.repositories.session_repo import SessionRepository
from server.app.schemas.user_schemas.auth_dto import TokenResponse, AuthVerifyCode, TokenRefreshRequest


class AuthService:
    # Имитация кэша кодов на уровне синглтона/сервиса
    VERIFICATION_CODES = {}

    def __init__(self, db_emp: AsyncSession, session_repo: SessionRepository):
        self.db_emp = db_emp
        self.session_repo = session_repo

    async def generate_verification_code(self, phone_number: str) -> str:
        """Бизнес-логика запроса и генерации OTP-кода"""
        # 1. Проверяем сотрудника в кадровой БД
        result = await self.db_emp.execute(select(Employee).where(Employee.phone_number == phone_number))
        employee = result.scalar_one_or_none()

        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Сотрудник с таким номером телефона не найден в базе кадров."
            )

        if not employee.chat_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Вы не активировали Telegram-бота. Сначала запустите бота на вашем телефоне."
            )

        # 2. Генерация 4-значного кода
        generated_code = str(secrets.randbelow(9000) + 1000)

        # 3. Запись в кэш на 5 минут
        expire_time = datetime.now(timezone.utc) + timedelta(minutes=5)
        self.VERIFICATION_CODES[phone_number] = {
            "code": generated_code,
            "expires_at": expire_time,
            "employee_id": employee.id  # Сохраняем ID, чтобы не делать повторный запрос при валидации
        }

        # Вывод в лог для Разработчика 3 (Telegram Bot)
        print(f"[DEBUG LOG] Код {generated_code} сгенерирован для chat_id {employee.chat_id}")
        return generated_code

    async def verify_code_and_login(self, payload: AuthVerifyCode) -> TokenResponse:
        """Бизнес-логика проверки кода и открытия сессии"""
        cached_data = self.VERIFICATION_CODES.get(payload.phone_number)
        if not cached_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Код не запрашивался или устарел.")

        if datetime.now(timezone.utc) > cached_data["expires_at"]:
            self.VERIFICATION_CODES.pop(payload.phone_number, None)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Срок действия кода истек.")

        if cached_data["code"] != payload.code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный код подтверждения.")

        # Код успешный — вытаскиваем сохраненный ID сотрудника и чистим кэш
        employee_id = cached_data["employee_id"]
        self.VERIFICATION_CODES.pop(payload.phone_number, None)

        # Генерируем тестовый Access JWT токен
        access_token = f"access_secret_jwt_for_id_{employee_id}"
        refresh_token = None

        # Управление долгосрочной сессией ("Запомнить меня")
        if payload.remember_me:
            refresh_token = secrets.token_urlsafe(64)
            expires_at = datetime.now(timezone.utc) + timedelta(days=30)

            new_session = UserSession(
                employee_id=employee_id,
                refresh_token=refresh_token,
                device_info=payload.device_info,
                expires_at=expires_at
            )
            await self.session_repo.create(new_session)
            await self.session_repo.db.commit()  # Коммитим сессию в db_documents

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def refresh_access_token(self, payload: TokenRefreshRequest) -> TokenResponse:
        """Обновление протухшего access-токена по рефрешу"""
        session = await self.session_repo.get_by_token(payload.refresh_token)
        if not session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия не найдена. Авторизуйтесь заново.")

        # Проверка валидности по времени
        db_expires = session.expires_at.replace(tzinfo=timezone.utc) if session.expires_at.tzinfo is None else session.expires_at
        if datetime.now(timezone.utc) > db_expires:
            await self.session_repo.delete(session)
            await self.session_repo.db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Срок действия сессии истек.")

        new_access_token = f"access_secret_jwt_for_id_{session.employee_id}"
        return TokenResponse(access_token=new_access_token, refresh_token=session.refresh_token)

    async def terminate_session(self, refresh_token: str) -> None:
        """Уничтожение сессии при Logout"""
        session = await self.session_repo.get_by_token(refresh_token)
        if session:
            await self.session_repo.delete(session)
            await self.session_repo.db.commit()