import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from starlette import status

from server.app.repositories.document_repo import DocumentRepository

logger = logging.getLogger(__name__)

class WorkflowService:
    def __init__(self, repo: DocumentRepository):
        self.repo = repo

    async def _verify_document_and_access(self, doc_id: int, user_id: int):
        """
        Проверяет существование документа и наличие прав у пользователя.
        Сначала гарантирует 404, если документа нет, а затем 403, если нет прав.
        """
        document = await self.repo.get_by_id(doc_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Документ не найден."
            )

        has_access = await self.repo.check_user_has_role(doc_id, user_id)
        if not has_access:
            logger.warning(
                f"Access denied for user_id={user_id} on doc_id={doc_id}",
                extra={"event_type": "workflow_access_denied", "doc_id": doc_id, "user_id": user_id}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="У вас нет прав для взаимодействия с этим документом."
            )
        return document

    async def toggle_completion(self, doc_id: int, user_id: int, is_completed: bool) -> None:
        """Отметка о выполнении задачи по документу"""
        await self._verify_document_and_access(doc_id, user_id)

        relation = await self.repo.get_user_relation(doc_id, user_id)
        if not relation:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Вы не являетесь участником процесса по данному документу."
            )

        relation.is_completed = is_completed
        relation.completed_at = datetime.now(timezone.utc) if is_completed else None

        try:
            await self.repo.db.commit()
            logger.info(
                f"User user_id={user_id} set completion status to {is_completed} for doc_id={doc_id}",
                extra={
                    "event_type": "task_completion_toggled",
                    "doc_id": doc_id,
                    "user_id": user_id,
                    "is_completed": is_completed
                }
            )
        except Exception as e:
            await self.repo.db.rollback()
            logger.error(
                f"Error toggling completion for doc_id={doc_id} by user_id={user_id}: {str(e)}",
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при обновлении статуса выполнения задачи."
            )

    async def mark_document_as_read(self, doc_id: int, user_id: int) -> None:
        """Фиксация прочтения документа пользователем"""
        await self._verify_document_and_access(doc_id, user_id)

        try:
            await self.repo.add_read_entry(doc_id, user_id)
            await self.repo.db.commit()

            logger.info(
                f"User user_id={user_id} marked doc_id={doc_id} as read",
                extra={
                    "event_type": "document_marked_as_read",
                    "doc_id": doc_id,
                    "user_id": user_id
                }
            )
        except Exception as e:
            await self.repo.db.rollback()
            logger.error(
                f"Error marking doc_id={doc_id} as read by user_id={user_id}: {str(e)}",
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при отметке документа как прочитанного."
            )

    async def get_unread_counts(self, user_id: int) -> list[dict[str, Any]]:
        """Получение количества непрочитанных документов по группам"""
        rows = await self.repo.get_unread_counts_by_group(user_id)
        return [
            {"type_id": r.type_id, "direction": r.direction, "count": r.count}
            for r in rows
        ]

    async def toggle_archive_status(self, doc_id: int, user_id: int, archive: bool) -> None:
        """Перемещение документа в архив или извлечение из него"""
        await self._verify_document_and_access(doc_id, user_id)

        try:
            if archive:
                await self.repo.archive_document(doc_id, user_id)
            else:
                await self.repo.unarchive_document(doc_id, user_id)

            await self.repo.db.commit()

            event_type = "document_archived" if archive else "document_unarchived"
            logger.info(
                f"User user_id={user_id} changed archive status (archive={archive}) for doc_id={doc_id}",
                extra={
                    "event_type": event_type,
                    "doc_id": doc_id,
                    "user_id": user_id,
                    "archive": archive
                }
            )
        except Exception as e:
            await self.repo.db.rollback()
            logger.error(
                f"Error toggling archive status for doc_id={doc_id} by user_id={user_id}: {str(e)}",
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при изменении статуса архивации документа."
            )

    async def toggle_pin(self, doc_id: int, user_id: int, pin: bool) -> None:
        """Закрепление или открепление документа в интерфейсе пользователя"""
        await self._verify_document_and_access(doc_id, user_id)

        try:
            if pin:
                await self.repo.pin_document(doc_id, user_id)
            else:
                await self.repo.unpin_document(doc_id, user_id)

            await self.repo.db.commit()

            event_type = "document_pinned" if pin else "document_unpinned"
            logger.info(
                f"User user_id={user_id} changed pin status (pin={pin}) for doc_id={doc_id}",
                extra={
                    "event_type": event_type,
                    "doc_id": doc_id,
                    "user_id": user_id,
                    "pin": pin
                }
            )
        except Exception as e:
            await self.repo.db.rollback()
            logger.error(
                f"Error toggling pin status for doc_id={doc_id} by user_id={user_id}: {str(e)}",
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при изменении состояния закрепления документа."
            )