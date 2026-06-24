from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from datetime import date

from server.app.database.document_models import DocStatus, DocDirection, AppRights
from server.app.deps import get_current_user, get_doc_service, get_registry_service
from server.app.role_checker import RoleChecker
from server.app.schemas.doc.document_dto import (
    DocumentListItem, DocumentCreateForm, DocumentDetailRead,
    AdminMetadataUpdate, DocumentPaginationResponse
)
from server.app.schemas.user_schemas.employee_dto import CurrentUser

# Импортируем обновленные сервисы СЭД
from server.app.services.documents.document_service import DocumentService
from server.app.services.documents.registry_service import DocumentRegistryService

router = APIRouter(prefix="/documents", tags=["Documents"])


# --- ЭНДПОИНТЫ КАРТОЧКИ ДОКУМЕНТА ---

@router.post("/", response_model=DocumentListItem, status_code=status.HTTP_201_CREATED)
async def create_document(
        payload: DocumentCreateForm,
        current_user: CurrentUser = Depends(get_current_user),
        service: DocumentService = Depends(get_doc_service)
):
    """Создание новой карточки документа во внутреннем контуре"""
    return await service.create(payload, current_user.id)


@router.get("/", response_model=DocumentPaginationResponse)
async def get_documents(
        scope: str = "my",
        is_completed: Optional[bool] = None,
        status_filters: Optional[List[DocStatus]] = Query(None),
        type_id: Optional[int] = None,
        direction: Optional[DocDirection] = None,
        tag_ids: Optional[List[int]] = Query(None),
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        limit: int = Query(20, ge=1, le=100, description="Размер страницы"),
        offset: int = Query(0, ge=0, description="Смещение выборки"),
        current_user: CurrentUser = Depends(get_current_user),
        service: DocumentRegistryService = Depends(get_registry_service)
):
    """Реестр документов с динамической фильтрацией и пагинацией для PyQt6 таблиц"""
    total, items = await service.get_all_paginated(
        user_id=current_user.id,
        user_rights=current_user.rights,
        is_completed=is_completed,
        status_filters=status_filters,
        type_id=type_id,
        direction=direction,
        tag_ids=tag_ids,
        date_from=date_from,
        date_to=date_to,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=limit,
        offset=offset
    )
    return {"total": total, "limit": limit, "offset": offset, "items": items}


@router.get("/{doc_id}", response_model=DocumentDetailRead)
async def get_document_by_id(
        doc_id: int,
        current_user: CurrentUser = Depends(get_current_user),
        service: DocumentService = Depends(get_doc_service)
):
    """Получение детальной информации о документе с фиксацией прочтения"""
    return await service.get_by_id(doc_id, current_user.id, current_user.rights)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
        doc_id: int,
        admin_user: CurrentUser = Depends(RoleChecker([AppRights.admin, AppRights.superadmin])),
        service: DocumentService = Depends(get_doc_service)
):
    """Удаление документа администратором системы"""
    await service.delete(doc_id)
    return None


@router.put("/{document_id}/admin-metadata", response_model=DocumentListItem)
async def admin_update_metadata(
        document_id: int,
        payload: AdminMetadataUpdate,
        admin_user: CurrentUser = Depends(RoleChecker([AppRights.admin, AppRights.superadmin])),
        service: DocumentService = Depends(get_doc_service)
):
    """Административное редактирование метаданных в обход ограничений состояний"""
    return await service.admin_update_metadata(document_id, payload)




