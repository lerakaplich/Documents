from fastapi import APIRouter, Depends, status
from typing import List, Optional

from server.app.deps import get_current_user, get_workflow_service
from server.app.schemas.doc.document_dto import (
    RedirectHistoryRead
)
from server.app.schemas.user_schemas.employee_dto import CurrentUser

# Импортируем обновленные сервисы СЭД
from server.app.services.documents.workflow_service import DocumentWorkflowService

router = APIRouter(prefix="/delegation", tags=["Documents"])

# --- ЭНДПОИНТЫ ДЕЛЕГИРОВАНИЯ ---


@router.get("/{document_id}/history", response_model=List[RedirectHistoryRead])
async def get_redirect_history(
        document_id: int,
        current_user: CurrentUser = Depends(get_current_user),
        service: DocumentWorkflowService = Depends(get_workflow_service)
):
    """История движений документа"""
    return await service.get_history(document_id)


@router.post("/{document_id}", status_code=status.HTTP_201_CREATED)
async def add_delegate(
        document_id: int,
        to_employee_id: int, # В теле запроса (Pydantic модель)
        message: Optional[str] = None,
        current_user: CurrentUser = Depends(get_current_user),
        service: DocumentWorkflowService = Depends(get_workflow_service)
):
    """Назначить сотрудника участником/делегатом"""
    await service.add_delegate(document_id, current_user.id, to_employee_id, message)
    return {"status": "success", "message": "Сотрудник добавлен в список участников"}

@router.delete("/{document_id}/{emp_id}")
async def remove_delegate(
        document_id: int,
        emp_id: int,
        current_user: CurrentUser = Depends(get_current_user),
        service: DocumentWorkflowService = Depends(get_workflow_service)
):
    """Отозвать права участника (только если есть права на управление)"""
    await service.remove_delegate(document_id, current_user.id, emp_id)
    return {"status": "success", "message": "Сотрудник удален из списка участников"}