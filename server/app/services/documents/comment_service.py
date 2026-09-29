import logging

from fastapi import HTTPException, status
from typing import Any
from sqlalchemy import select

from server.app.database.document_models import Comment, SystemEmployee
from server.app.repositories.comment_repo import CommentRepository
from server.app.services.common.notification_service import NotificationService

logger = logging.getLogger("app.services.comment_service")

class CommentService:
    def __init__(
        self,
        repo: CommentRepository,
        notification_service: NotificationService
    ):
        self.repo = repo
        self.notifications = notification_service

    async def create_comment(self, document_id: int, user_id: int, text: str) -> Comment:
        """Бизнес-логика создания записи комментария/замечания"""
        clean_text = text.strip() if text else ""
        if not clean_text:
            logger.warning(
                f"Attempt to create empty comment on doc_id={document_id} by user_id={user_id}",
                extra={"event_type": "comment_validation_failed", "doc_id": document_id, "user_id": user_id}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Текст правок не может быть пустым."
            )

        try:
            # 1. Создаем комментарий в БД
            comment = await self.repo.create(
                document_id=document_id,
                employee_id=user_id,
                text_content=clean_text
            )

            # 2. Фиксируем транзакцию
            await self.repo.db.commit()

            logger.info(
                f"Created comment id={comment.id} on doc_id={document_id} by user_id={user_id}",
                extra={
                    "event_type": "comment_created",
                    "comment_id": comment.id,
                    "doc_id": document_id,
                    "user_id": user_id,
                    "text_length": len(clean_text)
                }
            )
        except Exception as e:
            await self.repo.db.rollback()
            logger.exception(
                f"Failed to create comment on doc_id={document_id} by user_id={user_id}: {e}",
                extra={"event_type": "comment_create_error", "doc_id": document_id, "user_id": user_id}
            )
            raise

        # 3. Отправляем уведомления (изолируем ошибку, чтобы отправка нотификации не ломала ответ клиенту)
        try:
            await self.notifications.notify_comment_added(
                doc_id=document_id,
                author_id=user_id,
                comment_text=clean_text
            )
            logger.debug(
                f"Dispatched comment notifications for doc_id={document_id}",
                extra={"event_type": "comment_notify_dispatched", "doc_id": document_id, "comment_id": comment.id}
            )
        except Exception as e:
            logger.error(
                f"Failed to send comment notification for doc_id={document_id}, comment_id={comment.id}: {e}",
                extra={"event_type": "comment_notify_error", "doc_id": document_id, "comment_id": comment.id},
                exc_info=True
            )

        return comment

    async def get_document_comments(self, document_id: int) -> list[Comment]:
        """Получить список сырых комментариев к документу"""
        logger.debug(
            f"Fetching raw comments for doc_id={document_id}",
            extra={"event_type": "comment_get_raw_start", "doc_id": document_id}
        )
        comments = await self.repo.get_all_by_document_id(document_id)
        logger.debug(
            f"Retrieved {len(comments)} raw comments for doc_id={document_id}",
            extra={"event_type": "comment_get_raw_success", "doc_id": document_id, "count": len(comments)}
        )
        return comments

    async def get_document_comments_with_authors(self, document_id: int) -> list[dict[str, Any]]:
        """
        Получить историю замечаний с отформатированным ФИО автора (Фамилия И. О.)
        через локальную таблицу system_employees.
        """
        comments = await self.repo.get_all_by_document_id(document_id)
        if not comments:
            logger.debug(
                f"No comments found for doc_id={document_id}",
                extra={"event_type": "comment_get_history_empty", "doc_id": document_id}
            )
            return []

        author_ids = list({c.employee_id for c in comments})

        # Запрос авторов
        query = select(SystemEmployee).where(SystemEmployee.id.in_(author_ids))
        result = await self.repo.db.execute(query)
        authors_map = {emp.id: emp for emp in result.scalars().all()}

        history = []
        for comment in comments:
            author = authors_map.get(comment.employee_id)

            if author:
                init_f = f"{author.first_name[0].upper()}." if author.first_name else ""
                init_p = f"{author.patronymic[0].upper()}." if author.patronymic else ""
                author_fio = f"{author.last_name} {init_f}{init_p}".strip()
            else:
                logger.warning(
                    f"Employee id={comment.employee_id} not found in system_employees table for comment_id={comment.id}",
                    extra={
                        "event_type": "comment_author_not_found",
                        "comment_id": comment.id,
                        "missing_employee_id": comment.employee_id
                    }
                )
                author_fio = "Неизвестный сотрудник"

            history.append({
                "id": comment.id,
                "text": comment.text,
                "created_at": comment.created_at,
                "author_fio": author_fio
            })

        logger.debug(
            f"Formatted {len(history)} comments with author details for doc_id={document_id}",
            extra={"event_type": "comment_get_history_success", "doc_id": document_id, "count": len(history)}
        )
        return history

    async def delete_comment(self, comment_id: int, user_id: int) -> None:
        """Бизнес-логика удаления комментария с проверкой авторства"""
        comment = await self.repo.get_by_id(comment_id)

        if not comment:
            logger.warning(
                f"Attempted to delete non-existent comment_id={comment_id} by user_id={user_id}",
                extra={"event_type": "comment_not_found", "comment_id": comment_id, "user_id": user_id}
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Комментарий не найден."
            )

        if comment.employee_id != user_id:
            logger.warning(
                f"User user_id={user_id} attempted to delete comment_id={comment_id} belonging to user_id={comment.employee_id}",
                extra={
                    "event_type": "comment_delete_forbidden",
                    "comment_id": comment_id,
                    "attempted_by_user_id": user_id,
                    "actual_author_id": comment.employee_id
                }
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Вы можете удалять только собственные комментарии."
            )

        doc_id = comment.document_id
        try:
            await self.repo.delete(comment_id)
            await self.repo.db.commit()

            logger.info(
                f"Successfully deleted comment_id={comment_id} from doc_id={doc_id} by user_id={user_id}",
                extra={
                    "event_type": "comment_deleted",
                    "comment_id": comment_id,
                    "doc_id": doc_id,
                    "user_id": user_id
                }
            )
        except Exception as e:
            await self.repo.db.rollback()
            logger.exception(
                f"Failed to delete comment_id={comment_id}: {e}",
                extra={"event_type": "comment_delete_error", "comment_id": comment_id, "user_id": user_id}
            )
            raise
