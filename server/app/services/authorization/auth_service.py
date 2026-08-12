import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import httpx
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from cachetools import TTLCache

from server.app.config import TELEGRAM_BOT_TOKEN
from server.app.core.security_tokens import verify_password, create_access_token
from server.app.core.utils import mask_phone_number
from server.app.database.document_models import UserSession
from server.app.database.employee_models import Employee, EmployeePosition
from server.app.repositories.session_repo import SessionRepository
from server.app.schemas.user_schemas.auth_dto import TokenResponse, TokenRefreshRequest, UserLoginRequest, \
    PasswordChangeRequest, ResetPasswordConfirm, VerifyResetCodeRequest

logger = logging.getLogger("app.services.auth")

reset_codes_storage: TTLCache[str, dict[str, Any]] = TTLCache(maxsize=10000, ttl=600)

class AuthService:
    def __init__(self, db_emp: AsyncSession, session_repo: SessionRepository):
        self.db_emp = db_emp
        self.session_repo = session_repo

    async def _check_leader_status(self, employee_id: int) -> bool:
        """Проверяет по базе должность руководителя"""
        result = await self.db_emp.execute(
            select(EmployeePosition.is_leader)
            .where(EmployeePosition.employee_id == employee_id, EmployeePosition.is_leader == True)
        )
        return result.scalar_one_or_none() is not None

    async def authenticate_by_password(self, payload: UserLoginRequest) -> TokenResponse:
        """Проверяет логин/пароль и создает сессию"""
        # 1. Ищем активного сотрудника по нормализованному телефону
        result = await self.db_emp.execute(
            select(Employee).where(Employee.phone_number == payload.phone_number, Employee.is_active == True)
        )
        employee = result.scalar_one_or_none()

        # 2. Если не найден или пароль не совпал — отдаем общую ошибку (в целях безопасности)
        if not employee or not verify_password(payload.password, employee.password_hash):
            masked_phone = mask_phone_number(payload.phone_number)

            logger.warning(
                f"Failed login attempt for phone number {masked_phone}",
                extra={
                    "event_type": "auth_failed",
                    "phone_number": masked_phone,  # Маскируем и в extra!
                    "reason": "user_not_found" if not employee else "invalid_password",
                    "device_info": payload.device_info
                }
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный номер телефона или пароль."
            )

        # 3. Вычисляем динамические права руководителя
        is_leader = await self._check_leader_status(int(employee.id))

        # 4. Генерируем access-токен (кастуем к str из-за Mapped)
        access_token = create_access_token(int(employee.id), str(employee.service_number), is_leader)
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

        logger.info(
            f"User id={employee.id} (tab_num={employee.service_number}) logged in successfully",
            extra={
                "event_type": "auth_success",
                "employee_id": employee.id,
                "service_number": str(employee.service_number),
                "remember_me": payload.remember_me,
                "device_info": payload.device_info
            }
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )

    async def refresh_access_token(self, payload: TokenRefreshRequest) -> TokenResponse:
        """Обновляет пару токенов по действующему refresh-токену"""
        session = await self.session_repo.get_by_token(payload.refresh_token)
        if not session:
            logger.warning(
                "Token refresh failed: Session not found",
                extra={"event_type": "refresh_failed", "reason": "session_not_found"}
            )
            raise HTTPException(status_code=401, detail="Сессия не найдена.")

        db_expires = session.expires_at.replace(
            tzinfo=timezone.utc) if session.expires_at.tzinfo is None else session.expires_at

        if datetime.now(timezone.utc) > db_expires:
            logger.warning(
                f"Token refresh failed: Session expired for employee_id={session.employee_id}",
                extra={"event_type": "refresh_failed", "employee_id": session.employee_id, "reason": "session_expired"}
            )

            await self.session_repo.delete(session)
            await self.session_repo.db.commit()
            raise HTTPException(status_code=401, detail="Срок действия сессии истек.")

        # Проверяем, что сотрудник всё ещё активен
        result = await self.db_emp.execute(
            select(Employee).where(Employee.id == session.employee_id, Employee.is_active == True)
        )

        employee = result.scalar_one_or_none()
        if not employee:
            logger.warning(
                f"Token refresh blocked: Employee id={session.employee_id} is inactive or deleted",
                extra={"event_type": "refresh_blocked", "employee_id": session.employee_id}
            )
            raise HTTPException(status_code=403, detail="Пользователь заблокирован или не найден.")

        is_leader = await self._check_leader_status(session.employee_id)

        # Ротируем токены
        new_access_token = create_access_token(session.employee_id, str(employee.service_number), is_leader)
        new_refresh_token = secrets.token_urlsafe(64)

        session.refresh_token = new_refresh_token
        session.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        await self.session_repo.db.commit()

        logger.info(
            f"Token refreshed successfully for employee_id={session.employee_id}",
            extra={"event_type": "token_refreshed", "employee_id": session.employee_id}
        )

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer"
        )

    async def terminate_session(self, refresh_token: str) -> None:
        """Удаляет сессию при выходе из аккаунта"""
        session = await self.session_repo.get_by_token(refresh_token)
        if session:
            employee_id = session.employee_id
            await self.session_repo.delete(session)
            await self.session_repo.db.commit()

            logger.info(
                f"Session terminated for employee_id={employee_id}",
                extra={"event_type": "logout", "employee_id": employee_id}
            )

    async def change_user_password(self, employee_id: int, payload: PasswordChangeRequest) -> None:
        # Получаем сотрудника
        result = await self.db_emp.execute(select(Employee).where(Employee.id == employee_id))
        employee = result.scalar_one_or_none()

        if not employee:
            raise HTTPException(status_code=404, detail="Сотрудник не найден.")

        if not verify_password(payload.old_password, employee.password_hash):
            logger.warning(
                f"Password change failed: Incorrect old password for employee_id={employee_id}",
                extra={"event_type": "password_change_failed", "employee_id": employee_id}
            )
            raise HTTPException(status_code=400, detail="Неверно указан старый пароль.")

        # Хэшируем новый и сохраняем
        hashed_new = bcrypt.hashpw(payload.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        employee.password_hash = hashed_new

        # Закрываем все активные сессии пользователя на других устройствах ради безопасности!
        await self.session_repo.delete_all_for_employee(employee_id)
        await self.db_emp.commit()

        logger.info(
            f"Password changed and all active sessions terminated for employee_id={employee_id}",
            extra={"event_type": "password_changed", "employee_id": employee_id}
        )

    async def send_reset_code(self, phone_number: str) -> None:
        result = await self.db_emp.execute(select(Employee).where(Employee.phone_number == phone_number))
        employee = result.scalar_one_or_none()

        if not employee:
            logger.warning(
                f"Reset code requested for non-existent phone: {phone_number}",
                extra={"event_type": "reset_code_failed", "phone_number": phone_number, "reason": "user_not_found"}
            )
            raise HTTPException(status_code=404, detail="Пользователь с таким телефоном не найден.")

        if not employee.chat_id:
            logger.warning(
                f"Reset code failed: Telegram chat_id missing for employee_id={employee.id}",
                extra={"event_type": "reset_code_failed", "employee_id": employee.id, "reason": "no_telegram_chat_id"}
            )
            raise HTTPException(status_code=400, detail="Для восстановления пароля активируйте бота в Telegram.")

        # Генерируем 6-значный код
        reset_code = str(secrets.randbelow(900000) + 100000)

        # Сохраняем в наш простой словарь вместо otp_storage
        reset_codes_storage[phone_number] = {
            "code": reset_code,
            "employee_id": int(employee.id)
        }

        # Отправка HTTP-запроса в Telegram
        tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.post(tg_url, json={
                    "chat_id": int(employee.chat_id),
                    "text": f"🔐 Запрос на сброс пароля в СЭД.\n\nВаш код подтверждения: {reset_code}"
                })
                if response.status_code != 200:
                    logger.error(
                        f"Telegram API returned non-200 status code {response.status_code}: {response.text}",
                        extra={"event_type": "telegram_api_error", "employee_id": employee.id, "status_code": response.status_code}
                    )
                    raise HTTPException(status_code=500, detail="Ошибка отправки сообщения через Telegram-бот.")
            except httpx.RequestError as exc:
                logger.error(
                    f"Network error while connecting to Telegram API: {exc}",
                    exc_info=True,
                    extra={"event_type": "telegram_network_error", "employee_id": employee.id}
                )
                raise HTTPException(status_code=500, detail="Не удалось связаться с Telegram-ботом.")

        logger.info(
            f"Reset password code sent via Telegram to employee_id={employee.id}",
            extra={"event_type": "reset_code_sent", "employee_id": employee.id}
        )

    async def verify_reset_code(self, payload: VerifyResetCodeRequest) -> None:
        """Валидация кода сброса пароля без его сжигания."""
        cached_data = reset_codes_storage.get(payload.phone_number)
        masked_phone = mask_phone_number(payload.phone_number)

        if not cached_data or cached_data["code"] != payload.code:
            logger.warning(
                f"Reset code verification failed for phone {masked_phone}: Invalid or expired code",
                extra={
                    "event_type": "reset_code_verify_failed",
                    "phone_number": masked_phone,
                    "reason": "invalid_or_expired_code"
                }
            )
            # В случае ОШИБКИ стираем запись из кэша, чтобы предотвратить брутфорс
            reset_codes_storage.pop(payload.phone_number, None)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Неверный код подтверждения или срок его действия истек."
            )

        logger.info(
            f"Reset code verified successfully for phone {masked_phone}",
            extra={"event_type": "reset_code_verified", "phone_number": masked_phone}
        )

    async def reset_password_by_code(self, payload: ResetPasswordConfirm) -> None:
        """Сброс пароля по коду из Telegram."""
        cached_data = reset_codes_storage.get(payload.phone_number)
        masked_phone = mask_phone_number(payload.phone_number)

        if not cached_data or cached_data["code"] != payload.code:
            logger.warning(
                f"Password reset failed for phone {masked_phone}: Invalid or expired code",
                extra={
                    "event_type": "password_reset_failed",
                    "phone_number": masked_phone,
                    "reason": "invalid_or_expired_code"
                }
            )
            # Удаляем ключ, если ввод был неверным
            reset_codes_storage.pop(payload.phone_number, None)
            raise HTTPException(status_code=400, detail="Неверный код сброса или срок его действия истек.")

        employee_id = cached_data["employee_id"]
        reset_codes_storage.pop(payload.phone_number, None)

        result = await self.db_emp.execute(select(Employee).where(Employee.id == employee_id))
        employee = result.scalar_one_or_none()

        if not employee:
            raise HTTPException(status_code=404, detail="Сотрудник не найден.")

        hashed_new = bcrypt.hashpw(payload.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        employee.password_hash = hashed_new

        await self.session_repo.delete_all_for_employee(employee_id)
        await self.db_emp.commit()

        logger.info(
            f"Password successfully reset using Telegram code for employee_id={employee_id}",
            extra={"event_type": "password_reset_success", "employee_id": employee_id}
        )