from fastapi import HTTPException, status
from typing import List, Dict, Any
from sqlalchemy import select

from server.app.config import MSG_TEMPLATE_NEW_REVISION
from server.app.database.document_models import Comment, EmployeeDocument, SystemEmployee
from server.app.schemas.doc.document_dto import DocumentListItem
from server.app.repositories.comment_repo import CommentRepository


class CommentService:
    def __init__(self, repo: CommentRepository):
        self.repo = repo  # Внедряем репозиторий, управляющий сущностями Comment

    async def create_comment(self, document_id: int, user_id: int, text: str) -> Comment:
        """Бизнес-логика создания записи комментария/замечания"""
        if not text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Текст правок не может быть пустым."
            )

        # Используем метод create нашего обновленного репозитория
        return await self.repo.create(
            document_id=document_id,
            employee_id=user_id,
            text_content=text.strip()
        )

    async def get_document_comments(self, document_id: int) -> List[Comment]:
        """Получить список сырых комментариев к документу"""
        return await self.repo.get_all_by_document_id(document_id)

    async def get_document_comments_with_authors(self, document_id: int) -> List[Dict[str, Any]]:
        """
        Получить историю замечаний с отформатированным ФИО автора (Фамилия И. О.)
        через локальную таблицу system_employees.
        """
        # 1. Забираем комментарии из репозитория
        comments = await self.repo.get_all_by_document_id(document_id)
        if not comments:
            return []

        # 2. Собираем уникальные ID авторов, чтобы вытащить их одним запросом
        author_ids = list({c.employee_id for c in comments})

        # 3. Делаем выборку авторов из локальной system_employees базы документов
        query = select(SystemEmployee).where(SystemEmployee.id.in_(author_ids))
        result = await self.repo.db.execute(query)  # repo.db используется для выполнения кастомных стыковочных запросов
        authors_map = {emp.id: emp for emp in result.scalars().all()}

        # 4. Форматируем историю для отправки в PyQt6 (согласно схеме CommentRead)
        history = []
        for comment in comments:
            author = authors_map.get(comment.employee_id)

            if author:
                init_f = f"{author.first_name}." if author.first_name else ""
                init_p = f" {author.patronymic}." if author.patronymic else ""
                author_fio = f"{author.last_name} {init_f}{init_p}".strip()
            else:
                author_fio = "Неизвестный сотрудник"

            history.append({
                "id": comment.id,
                "text": comment.text,
                "created_at": comment.created_at,
                "author_fio": author_fio
            })

        return history

    async def delete_comment(self, comment_id: int, user_id: int) -> None:
        """Бизнес-логика удаления комментария с проверкой авторства"""
        comment = await self.repo.get_by_id(comment_id)

        if not comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Комментарий не найден."
            )

        if comment.employee_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Вы можете удалять только собственные комментарии."
            )

        await self.repo.delete(comment_id)
        await self.repo.db.commit()  # Изолированная транзакция удаления
