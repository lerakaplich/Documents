from fastapi import APIRouter, Depends, status, Form
from typing import Optional

from server.app.deps import get_current_user, get_review_service, get_workflow_service, get_registry_service
from server.app.schemas.doc.document_dto import (
    ToggleCompletionPayload
)
from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.services.documents.registry_service import RegistryService

# Импортируем обновленные сервисы СЭД
from server.app.services.documents.review_service import DocumentReviewService
from server.app.services.documents.workflow_service import WorkflowService

router = APIRouter(prefix="/workflow", tags=["Documents"])


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

@router.post("/{doc_id}/read")
async def mark_read(
    doc_id: int,
    user: CurrentUser = Depends(get_current_user),
    workflow: WorkflowService = Depends(get_workflow_service)
):
    # Ограничение: пользователь должен иметь доступ к документу (проверяется внутри workflow или repo)
    await workflow.mark_document_as_read(doc_id, user.id)
    return {"status": "ok"}

@router.get("/unread-counts")
async def get_unread_counts(
    user: CurrentUser = Depends(get_current_user),
    workflow: WorkflowService = Depends(get_workflow_service)
):
    # Ограничения: любой авторизованный пользователь может видеть свои счетчики
    return await workflow.get_unread_counts(user.id)


@router.post("/{document_id}/toggle-completion", status_code=status.HTTP_200_OK)
async def toggle_completion(
        document_id: int,
        payload: ToggleCompletionPayload,
        current_user: CurrentUser = Depends(get_current_user),
        service: WorkflowService = Depends(get_workflow_service)
):
    """Переключение документа между вкладками 'В работе' и 'Архив'"""
    await service.toggle_completion(document_id, current_user.id, payload.is_completed)
    return {"status": "success", "message": "Статус отображения изменен"}

@router.post("/{doc_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
async def archive_doc(
    doc_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: WorkflowService = Depends(get_workflow_service)
):
    """Архивировать документ для текущего пользователя"""
    await service.toggle_archive_status(doc_id, current_user.id, archive=True)
    return None

@router.delete("/{doc_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
async def unarchive_doc(
    doc_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: WorkflowService = Depends(get_workflow_service)
):
    """Разархивировать документ для текущего пользователя"""
    await service.toggle_archive_status(doc_id, current_user.id, archive=False)
    return None

@router.post("/{doc_id}/pin", status_code=status.HTTP_204_NO_CONTENT)
async def pin_doc(
    doc_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: WorkflowService = Depends(get_workflow_service)
):
    await service.toggle_pin(doc_id, current_user.id, pin=True)

@router.delete("/{doc_id}/pin", status_code=status.HTTP_204_NO_CONTENT)
async def unpin_doc(
    doc_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: WorkflowService = Depends(get_workflow_service)
):
    await service.toggle_pin(doc_id, current_user.id, pin=False)

