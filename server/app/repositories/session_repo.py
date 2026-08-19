from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from server.app.database.document_models import UserSession


class SessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_token(self, token_hash: str) -> Optional[UserSession]:
        """Поиск сессии по хешу refresh-токена."""
        result = await self.db.execute(
            select(UserSession).where(UserSession.refresh_token == token_hash)
        )
        return result.scalar_one_or_none()

    async def get_by_device(self, employee_id: int, device_info: Optional[str]) -> Optional[UserSession]:
        """Поиск существующей сессии для конкретного устройства пользователя."""
        if not device_info:
            return None
        result = await self.db.execute(
            select(UserSession).where(
                UserSession.employee_id == employee_id,
                UserSession.device_info == device_info
            )
        )
        return result.scalar_one_or_none()

    async def create(self, session_obj: UserSession) -> UserSession:
        """Сохранение новой сессии"""
        self.db.add(session_obj)
        return session_obj

    async def delete(self, session_obj: UserSession) -> None:
        """Удаление сессии"""
        await self.db.delete(session_obj)

    async def delete_all_for_employee(self, employee_id: int) -> None:
        """Удаление всех сессий конкретного сотрудника (например, при смене пароля)"""
        await self.db.execute(
            delete(UserSession).where(UserSession.employee_id == employee_id)
        )