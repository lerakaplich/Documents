from fastapi import HTTPException, status
from datetime import datetime, timezone
from server.app.schemas.doc.document_dto import DocumentListItem
from server.app.database.document_models import DocumentRole, DocStatus
from server.app.repositories.document_repo import DocumentRepository
from server.app.services.common.security_service import SecurityService
from server.app.services.documents.comment_service import CommentService


class DocumentReviewService:
    def __init__(self, repo: DocumentRepository, comment_service: CommentService, security: SecurityService):
        self.repo = repo
        self.comment_service = comment_service
        self.security = security

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