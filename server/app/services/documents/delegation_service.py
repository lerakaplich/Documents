from fastapi import HTTPException, status
from typing import List
from server.app.database.document_models import DocumentRole
from server.app.repositories.document_repo import DocumentRepository
from server.app.schemas.doc.document_dto import RedirectHistoryRead


class DelegationService:
    def __init__(self, repo: DocumentRepository):
        self.repo = repo

    async def add_delegate(self, doc_id: int, actor_id: int, target_id: int, message: str = None):
        """Назначить сотрудника делегатом"""
        # 1. Проверяем права актора (только отправитель или текущий получатель могут назначать)
        relation = await self.repo.get_user_relation(doc_id, actor_id)
        if not relation or relation.role not in [DocumentRole.sender, DocumentRole.recipient]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет прав на управление делегатами.")

        existing_participants = await self.repo.get_participants(doc_id)
        if target_id in [p.employee_id for p in existing_participants]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Сотрудник уже является участником этого документа.")

        # 2. Попытка вставки
        was_inserted = await self.repo.assign_role_to_employee(doc_id, target_id, DocumentRole.delegate)

        if not was_inserted:
            # Если вставка не удалась, значит он уже в БД
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Этот сотрудник уже является участником документа."
            )

        # 3. Только если вставка удалась, пишем историю
        await self.repo.add_redirect_history(doc_id, actor_id, target_id, message)
        await self.repo.db.commit()

    async def remove_delegate(self, doc_id: int, actor_id: int, target_id: int):
        """Отозвать делегата"""
        relation = await self.repo.get_user_relation(doc_id, actor_id)
        if not relation or relation.role not in [DocumentRole.sender, DocumentRole.recipient]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет прав на удаление участников.")

        # Удаляем делегата
        await self.repo.remove_employee_from_doc(doc_id, target_id)

        # 4. Фиксируем в истории факт отзыва (опционально, для аудита)
        await self.repo.add_redirect_history(doc_id, actor_id, target_id, "Отозван доступ делегата")

        await self.repo.db.commit()

    async def get_history(self, doc_id: int) -> List[RedirectHistoryRead]:
        """Получить историю перенаправлений"""
        history_records = await self.repo.get_redirect_history(doc_id)
        return [RedirectHistoryRead.model_validate(h) for h in history_records]