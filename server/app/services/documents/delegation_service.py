from fastapi import HTTPException, status
from typing import List
from server.app.database.document_models import DocumentRole
from server.app.repositories.document_repo import DocumentRepository
from server.app.schemas.doc.document_dto import RedirectHistoryRead
from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.services.common.notification_service import NotificationService
from server.app.services.common.security_service import SecurityService


class DelegationService:
    def __init__(
        self,
        repo: DocumentRepository,
        security: SecurityService,
        notification_service: NotificationService
    ):
        self.repo = repo
        self.security = security
        self.notifications = notification_service

    async def _check_permissions(self, doc_id: int, actor: CurrentUser):
        """Проверка: Администратор ИЛИ участник с правами управления."""

        # 1. Пробуем проверить роль участника
        relation = await self.repo.get_user_relation(doc_id, actor.id)
        if relation and relation.role in [DocumentRole.sender, DocumentRole.recipient]:
            return  # Успех: пользователь — владелец/получатель

        # 2. Если не участник, проверяем админа
        await self.security.verify_is_admin(actor)

    async def add_delegate(self, doc_id: int, actor: CurrentUser, target_id: int, message: str = None):
        """Назначить сотрудника делегатом"""
        # 1. Проверяем права актора (только отправитель или текущий получатель могут назначать)
        await self._check_permissions(doc_id, actor)

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
        await self.repo.add_redirect_history(doc_id, actor.id, target_id, message)
        await self.repo.db.commit()

        await self.notifications.notify_delegation_changed(
            doc_id=doc_id,
            delegatee_id=target_id,
            is_granted=True,
            message=message
        )

    async def remove_delegate(self, doc_id: int, actor: CurrentUser, target_id: int):
        """Отозвать делегата"""
        await self._check_permissions(doc_id, actor)

        # Удаляем делегата
        await self.repo.remove_employee_from_doc(doc_id, target_id)

        # 4. Фиксируем в истории факт отзыва (опционально, для аудита)
        await self.repo.add_redirect_history(doc_id, actor.id, target_id, "Отозван доступ делегата")

        await self.repo.db.commit()

        await self.notifications.notify_delegation_changed(
            doc_id=doc_id,
            delegatee_id=target_id,
            is_granted=False
        )

    async def get_history(self, doc_id: int) -> List[RedirectHistoryRead]:
        """Получить историю перенаправлений"""
        history_records = await self.repo.get_redirect_history(doc_id)
        return [RedirectHistoryRead.model_validate(h) for h in history_records]