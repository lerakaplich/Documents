from fastapi import HTTPException, status
from datetime import datetime, timezone
from server.app.schemas.doc.document_dto import DocumentListItem
from server.app.database.document_models import DocumentRole, DocStatus
from server.app.repositories.document_repo import DocumentRepository
from server.app.services.comment_service import CommentService


class DocumentReviewService:
    def __init__(self, db_repo: DocumentRepository, comment_service: CommentService):
        self.repo = db_repo
        self.comment_service = comment_service

    async def process_review(self, document_id: int, user_id: int, approved: bool, comment_text: str = None):
        """Обработка решения согласующего лица (Утвердить / Отклонить)"""
        relation = await self.repo.get_user_relation(document_id, user_id)

        if not relation or relation.role not in [DocumentRole.recipient, DocumentRole.delegate]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ваша роль не требует согласования.")

        if relation.is_approved is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Вы уже приняли решение по этому документу.")

        # Фиксируем решение
        relation.is_approved = approved

        # Если при согласовании/отклонении был передан текстовый комментарий — сохраняем его
        if comment_text and comment_text.strip():
            await self.comment_service.create_comment(document_id, user_id, comment_text)
            document = await self.repo.get_by_id(document_id)
            if document:
                document.last_comment_text = comment_text.strip()

        # Автоматический пересчет статуса всего документа
        await self._recalculate_document_status(document_id)
        await self.repo.db.commit()

    async def make_revisions(self, document_id: int, user_id: int, text: str) -> None:
        """Внесение замечаний (правок) к документу без вынесения финального решения"""
        relation = await self.repo.get_user_relation(document_id, user_id)
        if not relation or relation.role not in [DocumentRole.recipient, DocumentRole.delegate]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Оставлять правки могут только согласующие лица.")

        document = await self.repo.get_by_id(document_id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден")

        # Создаем комментарий через CommentService
        await self.comment_service.create_comment(document_id, user_id, text)

        # Денормализация: сохраняем быстрый текст последней правки в документ
        document.last_comment_text = text.strip()

        try:
            await self.repo.db.commit()
        except Exception as e:
            await self.repo.db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Ошибка сохранения замечания: {str(e)}")

        dto_document = DocumentListItem.model_validate(document)

        # Отправляем уже валидный DTO
        await self.comment_service.send_notification_stub(dto_document)

    async def toggle_complete(self, doc_id: int, user_id: int, is_completed: bool) -> None:
        """Переключение состояния задачи сотрудника (В работе / В архив)"""
        relation = await self.repo.get_user_relation(doc_id, user_id)
        if not relation:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="Вы не являетесь участником этого документа.")

        relation.is_completed = is_completed
        relation.completed_at = datetime.now(timezone.utc) if is_completed else None
        await self.repo.db.commit()

    async def _recalculate_document_status(self, document_id: int):
        """Внутренний конечный автомат пересчета статусов веток согласования"""
        document = await self.repo.get_by_id(document_id)
        if not document:
            return

        # 1. Если есть хотя бы один жесткий отказ (False) -> Документ отклонен полностью
        if await self.repo.has_any_rejections(document_id):
            document.status = DocStatus.rejected
            return

        # 2. Если никто не отклонил и пустых решений (None) больше нет -> Полностью утвержден
        if not await self.repo.has_any_pending(document_id):
            document.status = DocStatus.approved
        else:
            # 3. Если пустые еще есть, но кто-то уже нажал "Утвердить" -> Частично утвержден
            if await self.repo.has_any_approvals(document_id, [DocumentRole.recipient, DocumentRole.delegate]):
                document.status = DocStatus.partially_approved
            else:
                document.status = DocStatus.under_review