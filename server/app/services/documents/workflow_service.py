from datetime import datetime, timezone
from fastapi import HTTPException
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