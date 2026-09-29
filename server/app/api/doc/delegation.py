from fastapi import APIRouter, Depends, status
from typing import Optional

from server.app.deps import get_current_user, get_delegation_service
from server.app.schemas.doc.document_dto import (
    RedirectHistoryRead, BulkDelegateCreate
)
from server.app.schemas.user_schemas.employee_dto import CurrentUser

# Импортируем обновленные сервисы СЭД
from server.app.services.documents.delegation_service import DelegationService

router = APIRouter(prefix="/delegation", tags=["Documents"])

# --- ЭНДПОИНТЫ ДЕЛЕГИРОВАНИЯ ---


@router.get("/{document_id}/history", response_model=list[RedirectHistoryRead])
async def get_redirect_history(
    document_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: DelegationService = Depends(get_delegation_service)
):
    """История движений документа"""
    return await service.get_history(document_id)


@router.post("/{document_id}", status_code=status.HTTP_201_CREATED)
async def add_delegates(
    document_id: int,
    data: BulkDelegateCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: DelegationService = Depends(get_delegation_service)
):
    """Назначить одного или нескольких сотрудников делегатами"""
    added_ids = await service.add_delegates_bulk(
        doc_id=document_id,
        actor=current_user,
        target_ids=data.target_ids,
        message=data.message
    )
    return {
        "status": "success",
        "message": f"Успешно добавлено участников: {len(added_ids)}",
        "added_employee_ids": added_ids
    }

@router.delete("/{document_id}/{emp_id}")
async def remove_delegate(
        document_id: int,
        emp_id: int,
        current_user: CurrentUser = Depends(get_current_user),
        service: DelegationService = Depends(get_delegation_service)
):
    """Отозвать права участника (только если есть права на управление)"""
    await service.remove_delegate(document_id, current_user, emp_id)
    return {"status": "success", "message": "Сотрудник удален из списка участников"}