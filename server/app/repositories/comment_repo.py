from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional
from server.app.database.document_models import Comment

class CommentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, comment_id: int) -> Optional[Comment]:
        """Получить один комментарий по ID"""
        result = await self.db.execute(select(Comment).where(Comment.id == comment_id))
        return result.scalar_one_or_none()

    async def get_all_by_document_id(self, document_id: int) -> List[Comment]:
        """Получить все комментарии к документу, отсортированные по времени создания"""
        query = (
            select(Comment)
            .where(Comment.document_id == document_id)
            .order_by(Comment.created_at.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, document_id: int, employee_id: int, text_content: str) -> Comment:
        """Создать новый комментарий/замечание к документу"""
        new_comment = Comment(
            document_id=document_id,
            employee_id=employee_id,  # Передаем ID сотрудника из db_employees
            text=text_content
        )
        self.db.add(new_comment)
        return new_comment

    async def delete(self, comment_id: int) -> None:
        """Прямое удаление комментария из базы"""
        await self.db.execute(delete(Comment).where(Comment.id == comment_id))