import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from server.app.config import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_SECRET_KEY, JWT_ALGORITHM
from server.app.database.document_models import UserSession
from server.app.database.employee_models import Employee, EmployeePosition
from server.app.repositories.session_repo import SessionRepository
from server.app.schemas.user_schemas.auth_dto import TokenResponse, TokenRefreshRequest, UserLoginRequest


class AuthService:
    def __init__(self, db_emp: AsyncSession, session_repo: SessionRepository):
        self.db_emp = db_emp
        self.session_repo = session_repo

    def _generate_jwt_access_token(self, employee_id: int, service_number: str, is_leader: bool) -> str:
        """Генерирует короткоживущий Access-токен"""
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": str(employee_id),
            "service_number": service_number,
            "is_leader": is_leader,
            "exp": expire
        }
        return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

    async def _check_leader_status(self, employee_id: int) -> bool:
        """Проверяет по базе должность руководителя"""
        result = await self.db_emp.execute(
            select(EmployeePosition.is_leader)
            .where(EmployeePosition.employee_id == employee_id, EmployeePosition.is_leader == True)
        )
        return result.scalar_one_or_none() is not None

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Безопасная проверка хэша пароля"""
        if not hashed_password:
            return False
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

    async def authenticate_by_password(self, payload: UserLoginRequest) -> TokenResponse:
        """Проверяет логин/пароль и создает сессию"""
        # 1. Ищем активного сотрудника по нормализованному телефону
        result = await self.db_emp.execute(
            select(Employee).where(Employee.phone_number == payload.phone_number, Employee.is_active == True)
        )
        employee = result.scalar_one_or_none()

        # 2. Если не найден или пароль не совпал — отдаем общую ошибку (в целях безопасности)
        if not employee or not self._verify_password(payload.password, employee.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный номер телефона или пароль."
            )

        # 3. Вычисляем динамические права руководителя
        is_leader = await self._check_leader_status(int(employee.id))

        # 4. Генерируем access-токен (кастуем к str из-за Mapped)
        access_token = self._generate_jwt_access_token(int(employee.id), str(employee.service_number), is_leader)
        refresh_token = None

        # 5. Если стоит галочка "Запомнить меня" — генерируем refresh-токен
        if payload.remember_me:
            refresh_token = secrets.token_urlsafe(64)
            new_session = UserSession(
                employee_id=employee.id,
                refresh_token=refresh_token,
                device_info=payload.device_info,
                expires_at=datetime.now(timezone.utc) + timedelta(days=30)
            )
            await self.session_repo.create(new_session)
            await self.session_repo.db.commit()

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )

    async def refresh_access_token(self, payload: TokenRefreshRequest) -> TokenResponse:
        """Обновляет пару токенов по действующему refresh-токену"""
        session = await self.session_repo.get_by_token(payload.refresh_token)
        if not session:
            raise HTTPException(status_code=401, detail="Сессия не найдена.")

        db_expires = session.expires_at.replace(
            tzinfo=timezone.utc) if session.expires_at.tzinfo is None else session.expires_at
        if datetime.now(timezone.utc) > db_expires:
            await self.session_repo.delete(session)
            await self.session_repo.db.commit()
            raise HTTPException(status_code=401, detail="Срок действия сессии истек.")

        # Проверяем, что сотрудник всё ещё активен
        result = await self.db_emp.execute(
            select(Employee).where(Employee.id == session.employee_id, Employee.is_active == True)
        )
        employee = result.scalar_one_or_none()
        if not employee:
            raise HTTPException(status_code=403, detail="Пользователь заблокирован или не найден.")

        is_leader = await self._check_leader_status(session.employee_id)

        # Ротируем токены
        new_access_token = self._generate_jwt_access_token(session.employee_id, str(employee.service_number), is_leader)
        new_refresh_token = secrets.token_urlsafe(64)

        session.refresh_token = new_refresh_token
        session.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        await self.session_repo.db.commit()

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer"
        )

    async def terminate_session(self, refresh_token: str) -> None:
        """Удаляет сессию при выходе из аккаунта"""
        session = await self.session_repo.get_by_token(refresh_token)
        if session:
            await self.session_repo.delete(session)
            await self.session_repo.db.commit()