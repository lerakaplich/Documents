import logging
from typing import Optional

from fastapi import HTTPException, status
from server.app.database.document_models import DocumentRole, DocStatus, DocumentStatusHistory
from server.app.repositories.document_repo import DocumentRepository
from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.services.common.security_service import SecurityService
from server.app.services.documents.comment_service import CommentService

# Наш технический логгер для консоли / Grafana Loki
audit_logger = logging.getLogger("sed_audit")

class DocumentReviewService:
    def __init__(self, repo: DocumentRepository, comment_service: CommentService, security: SecurityService):
        self.repo = repo
        self.comment_service = comment_service
        self.security = security

    async def get_document_status_history(self, document_id: int, current_user: CurrentUser) -> list:
        """Получение истории статусов документа (Доступно участникам документа ИЛИ администраторам)"""

        is_authorized = False

        # 1. Проверяем, является ли пользователь админом
        try:
            await self.security.verify_is_admin(current_user)
            is_authorized = True
        except HTTPException:
            # Если не админ, проверяем, является ли он обычным участником согласования
            pass

        # 2. Если не админ, проверяем стандартные права участника документа
        if not is_authorized:
            relation = await self.repo.get_user_relation(document_id, current_user.id)
            # Если у пользователя нет связи с документом, verify_can_review_document выбросит 403
            await self.security.verify_can_review_document(relation)

        # 3. Если проверки пройдены, забираем историю
        return await self.repo.get_status_history_by_doc_id(document_id)

    async def process_review(self, document_id: int, user_id: int, approved: bool, comment_text: str = None):
        # 1. Получаем связь
        relation = await self.repo.get_user_relation(document_id, user_id)

        # 2. Проверяем права через SecurityService
        await self.security.verify_can_review_document(relation)

        if relation.is_approved is not None:
            raise HTTPException(status_code=400, detail="Решение уже принято.")

        relation.is_approved = approved

        if comment_text and comment_text.strip():
            await self.comment_service.create_comment(document_id, user_id, comment_text)
            await self.repo.update_last_comment(document_id, comment_text)

        await self._recalculate_document_status(document_id)
        await self.repo.db.commit()

    async def make_revisions(self, document_id: int, user_id: int, text: str) -> None:
        """Внесение замечаний (правок) к документу без вынесения финального решения"""
        relation = await self.repo.get_user_relation(document_id, user_id)
        await self.security.verify_can_review_document(relation)

        document = await self.repo.get_by_id(document_id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

        # Создаем комментарий через CommentService
        await self.comment_service.create_comment(document_id, user_id, text)
        await self.repo.update_last_comment(document_id, text)

        try:
            await self.repo.db.commit()
        except Exception as e:
            await self.repo.db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Ошибка сохранения замечания: {str(e)}")

    async def change_status_manually(
            self,
            document_id: int,
            current_user: CurrentUser,  # Передаем объект целиком вместо user_id
            new_status: DocStatus,
            reason: Optional[str] = None
    ):
        """Ручное (административное) изменение статуса документа"""
        # 1. Проверяем, что действие совершает админ или суперадмин
        await self.security.verify_is_admin(current_user)

        document = await self.repo.get_by_id(document_id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

        old_status = document.status
        if old_status == new_status:
            return

        document.status = new_status

        # Пишем в бизнес-историю
        history_entry = DocumentStatusHistory(
            document_id=document_id,
            old_status=old_status,
            new_status=new_status,
            changed_by_employee_id=current_user.id,
            comment=reason or "Статус изменен вручную администратором."
        )
        await self.repo.add_status_history(history_entry)

        # Пишем в технический лог для Grafana
        audit_logger.info(
            "Статус документа изменен вручную администратором",
            extra={
                "action": "manual_document_status_changed",
                "document_id": document_id,
                "old_status": old_status.value,
                "new_status": new_status.value,
                "triggered_by_user_id": current_user.id,
                "reason": reason
            }
        )

        await self.repo.db.commit()

    async def _recalculate_document_status(self, document_id: int, changed_by_user_id: Optional[int] = None):
        """Внутренний конечный автомат пересчета статусов веток согласования"""
        document = await self.repo.get_by_id(document_id)
        if not document:
            return

        old_status = document.status

        # Вычисляем новый статус с нуля по приоритетам
        # 1. Если есть хотя бы один жесткий отказ (False) -> Документ отклонен полностью
        if await self.repo.has_any_rejections(document_id):
            new_status = DocStatus.rejected

        # 2. Если никто не отклонил и пустых решений (None) больше нет -> Полностью утвержден
        elif not await self.repo.has_any_pending(document_id):
            new_status = DocStatus.approved

        # 3. Если пустые еще есть, но кто-то уже нажал "Утвердить" -> Частично утвержден
        elif await self.repo.has_any_approvals(document_id, [DocumentRole.recipient, DocumentRole.delegate]):
            new_status = DocStatus.partially_approved

        else:
            # 4. Во всех остальных случаях статус остается на рассмотрении
            new_status = DocStatus.under_review

        # Теперь для IDE переменные old_status и new_status инициализированы из разных веток,
        # и предупреждение "Unreachable code" мгновенно исчезнет!
        if old_status != new_status:
            document.status = new_status

            # Формируем запись истории для базы данных
            history_entry = DocumentStatusHistory(
                document_id=document_id,
                old_status=old_status,
                new_status=new_status,
                changed_by_employee_id=changed_by_user_id,
                comment="Автоматический пересчет статуса на основе решений согласующих лиц."
            )
            await self.repo.add_status_history(history_entry)

            # Системный лог в консоль для Grafana
            audit_logger.info(
                "Статус документа изменен",
                extra={
                    "action": "document_status_changed",
                    "document_id": document_id,
                    "old_status": old_status.value if hasattr(old_status, 'value') else str(old_status),
                    "new_status": new_status.value if hasattr(new_status, 'value') else str(new_status),
                    "triggered_by_user_id": changed_by_user_id
                }
            )