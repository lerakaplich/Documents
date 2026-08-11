from datetime import datetime, timezone
from fastapi import HTTPException
from starlette import status

from server.app.repositories.document_repo import DocumentRepository
from server.app.services.documents.delegation_service import DelegationService

class WorkflowService:
    def __init__(self, repo: DocumentRepository, delegation_service: DelegationService):
        self.repo = repo
        self.delegation = delegation_service

    # --- Управление задачами (бывший toggle_complete) ---
    async def toggle_completion(self, doc_id: int, user_id: int, is_completed: bool) -> None:
        relation = await self.repo.get_user_relation(doc_id, user_id)
        if not relation:
            raise HTTPException(status_code=403, detail="Вы не участник документа.")

        relation.is_completed = is_completed
        relation.completed_at = datetime.now(timezone.utc) if is_completed else None
        await self.repo.db.commit()

    async def mark_document_as_read(self, doc_id: int, user_id: int) -> None:
        # Проверяем, имеет ли пользователь вообще отношение к этому документу
        relation = await self.repo.get_user_relation(doc_id, user_id)
        if not relation:
            raise HTTPException(status_code=403, detail="Доступ запрещен или документ не найден.")

        # Вызываем репозиторий для создания записи
        await self.repo.add_read_entry(doc_id, user_id)
        # Комитим изменения
        await self.repo.db.commit()

    async def get_unread_counts(self, user_id: int):
        rows = await self.repo.get_unread_counts_by_group(user_id)
        # Превращаем в удобную структуру [{"type_id": 1, "direction": "internal", "count": 5}, ...]
        return [
            {"type_id": r.type_id, "direction": r.direction, "count": r.count}
            for r in rows
        ]

    async def _verify_user_access(self, doc_id: int, user_id: int):
        """Выбрасывает 403, если у пользователя нет доступа к документу."""
        has_access = await self.repo.check_user_has_role(doc_id, user_id)
        if not has_access:
            # Уровень доступа: если нет роли, значит документ «чужой»
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="У вас нет прав для взаимодействия с этим документом."
            )

    async def toggle_archive_status(self, doc_id: int, user_id: int, archive: bool):
        """Сервисный метод для переключения архива"""
        await self._verify_user_access(doc_id, user_id)

        if archive:
            await self.repo.archive_document(doc_id, user_id)
        else:
            await self.repo.unarchive_document(doc_id, user_id)

    async def toggle_pin(self, doc_id: int, user_id: int, pin: bool):
        # 1. Логика проверки прав
        await self._verify_user_access(doc_id, user_id)

        # 2. Логика выполнения
        if pin:
            await self.repo.pin_document(doc_id, user_id)
        else:
            await self.repo.unpin_document(doc_id, user_id)