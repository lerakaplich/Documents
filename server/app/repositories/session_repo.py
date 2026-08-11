from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from server.app.database.document_models import UserSession


class SessionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_token(self, refresh_token: str) -> Optional[UserSession]:
        """Поиск активной сессии по refresh-токену"""
        result = await self.db.execute(
            select(UserSession).where(UserSession.refresh_token == refresh_token)
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