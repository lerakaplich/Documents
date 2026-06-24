from fastapi import APIRouter, Depends, status, Form
from typing import Optional

from server.app.deps import get_current_user, get_review_service
from server.app.schemas.doc.document_dto import (
    ToggleCompletionPayload
)
from server.app.schemas.user_schemas.employee_dto import CurrentUser

# Импортируем обновленные сервисы СЭД
from server.app.services.documents.review_service import DocumentReviewService
from server.app.services.documents.workflow_service import WorkflowService

router = APIRouter(prefix="/documents", tags=["Documents"])


# --- ЖИЗНЕННЫЙ ЦИКЛ, СОГЛАСОВАНИЕ И ЗАМЕЧАНИЯ ---



@router.post("/{document_id}/review", response_model=dict)
async def process_document_review(
        document_id: int,
        approved: bool = Form(..., description="Решение: True - утвердить, False - отклонить"),
        comment_text: Optional[str] = Form(None, description="Опциональный комментарий к решению"),
        current_user: CurrentUser = Depends(get_current_user),
        service: DocumentReviewService = Depends(get_review_service)
):
    """Вынесение финального вердикта по документу (Утвердить / Отклонить)"""
    await service.process_review(
        document_id=document_id,
        user_id=current_user.id,
        approved=approved,
        comment_text=comment_text
    )
    return {"status": "success", "message": "Ваше решение успешно зафиксировано"}




@router.post("/{document_id}/toggle-completion", status_code=status.HTTP_200_OK)
async def toggle_completion(
        document_id: int,
        payload: ToggleCompletionPayload,
        current_user: CurrentUser = Depends(get_current_user),
        service: WorkflowService = Depends(get_review_service)
):
    """Переключение документа между вкладками 'В работе' и 'Архив'"""
    await service.toggle_completion(document_id, current_user.id, payload.is_completed)
    return {"status": "success", "message": "Статус отображения изменен"}


