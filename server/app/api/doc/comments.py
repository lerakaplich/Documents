from fastapi import APIRouter, Depends, Form
from typing import List

from server.app.deps import get_current_user, get_review_service, \
    get_comment_service
from server.app.schemas.user_schemas.employee_dto import CurrentUser

# Импортируем обновленные сервисы СЭД
from server.app.services.documents.review_service import DocumentReviewService
from server.app.services.documents.comment_service import CommentService

router = APIRouter(prefix="/comments", tags=["Documents"])

@router.post("/{document_id}/edit", response_model=dict)
async def make_document_revisions(
        document_id: int,
        text: str = Form(..., description="Текст вносимых правок/замечаний"),
        current_user: CurrentUser = Depends(get_current_user),
        service: DocumentReviewService = Depends(get_review_service)
):
    """Внесение правок согласующим лицом без вынесения итогового решения"""
    await service.make_revisions(document_id=document_id, user_id=current_user.id, text=text)
    return {"status": "success", "message": "Правки успешно добавлены в историю документа"}


@router.get("/{document_id}", response_model=List[dict])
async def get_document_comments_history(
        document_id: int,
        current_user: CurrentUser = Depends(get_current_user),
        comment_svc: CommentService = Depends(get_comment_service)
):
    """Получить полную историю замечаний к документу с расшифрованными ФИО авторов"""
    return await comment_svc.get_document_comments_with_authors(document_id)
