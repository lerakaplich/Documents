from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from typing import List

from server.app.config import MSG_TEMPLATE_NEW_REVISION
from server.app.database.models import Comment, EmployeeDocument
from server.app.schemas.doc_schemas.document_dto import DocumentListItem


class CommentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_comment(self, document_id: int, user_id: int, text: str) -> Comment:
        """Чистый инсерт записи в public.comments"""
        if not text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Текст правок не может быть пустым."
            )

        new_comment = Comment(
            document_id=document_id,
            employee_id=user_id,
            text=text.strip()
        )
        self.db.add(new_comment)
        return new_comment

    async def get_document_comments(self, document_id: int) -> List[Comment]:
        """
        C[R]UD: Получить все комментарии к документу (для ленты истории в PyQt6)
        """
        query = select(Comment).where(Comment.document_id == document_id).order_by(Comment.created_at.asc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def delete_comment(self, comment_id: int, user_id: int) -> None:
        """
        CRU[D]: Удалить комментарий (например, если сотрудник хочет стереть свою ошибку)
        """
        query = select(Comment).where(Comment.id == comment_id)
        result = await self.db.execute(query)
        comment = result.scalar_one_or_none()

        if not comment:
            raise HTTPException(status_code=404, detail="Комментарий не найден.")

        # Проверяем, что удаляет именно тот, кто написал
        if comment.employee_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Вы можете удалять только собственные комментарии."
            )

        await self.db.execute(delete(Comment).where(Comment.id == comment_id))

    async def send_notification_stub(self, document: DocumentListItem):
        """Заглушка рассылки пушей"""
        try:
            query = select(EmployeeDocument.employee_id).where(
                EmployeeDocument.document_id == document.id
            )
            participant_ids = (await self.db.execute(query)).scalars().all()

            message_text = MSG_TEMPLATE_NEW_REVISION.format(
                reg_number=document.reg_number or f"ID-{document.id}",
                title=document.title or "Без названия"
            )
            print(f"[TG_BOT_LOG] Новые замечания к документу для участников {participant_ids}")
            print(f"[TG_BOT_LOG] Текст: {message_text}")
        except Exception as e:
            print(f"[TG_BOT_ERROR] {str(e)}")