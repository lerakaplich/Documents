from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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