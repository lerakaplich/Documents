from fastapi import APIRouter, Depends, status, Query
from typing import Optional
from datetime import date

from server.app.database.document_models import DocStatus, DocDirection, AppRights
from server.app.deps import get_current_user, get_doc_service, get_registry_service
from server.app.role_checker import RoleChecker
from server.app.schemas.doc.document_dto import (
    DocumentListItem, DocumentCreateForm, DocumentDetailRead,
    AdminMetadataUpdate, DocumentPaginationResponse, ProposedNumberResponse, UnansweredDocumentStat
)
from server.app.schemas.user_schemas.employee_dto import CurrentUser

# Импортируем обновленные сервисы СЭД
from server.app.services.documents.document_service import DocumentService
from server.app.services.documents.registry_service import RegistryService

router = APIRouter(prefix="/documents", tags=["Documents"])


# --- ЭНДПОИНТЫ КАРТОЧКИ ДОКУМЕНТА ---

@router.post("/", response_model=DocumentListItem, status_code=status.HTTP_201_CREATED)
async def create_document(
        payload: DocumentCreateForm,
        current_user: CurrentUser = Depends(get_current_user),
        service: DocumentService = Depends(get_doc_service)
):
    """Создание новой карточки документа во внутреннем контуре"""
    return await service.create(payload, current_user)

@router.get("/proposed-number", response_model=ProposedNumberResponse)
async def get_proposed_document_number(
        type_id: int = Query(..., description="ID типа документа"),
        direction: DocDirection = Query(..., description="Направление документа (internal/external/etc.)"),
        current_user: CurrentUser = Depends(get_current_user),
        service: DocumentService = Depends(get_doc_service)
):
    """
    Возвращает проект регистрационного номера документа для текущего пользователя.
    """
    return await service.generate_proposed_number(
        type_id=type_id,
        direction=direction,
        user_id=current_user.id
    )

@router.get("/", response_model=DocumentPaginationResponse)
async def get_documents(
    scope: str = Query("my", description="Область видимости: 'my', 'all', 'archive', 'pinned'"),
    is_completed: Optional[bool] = Query(None, description="Фильтр завершенности"),
    status_filters: Optional[list[DocStatus]] = Query(default=None, description="Фильтр по статусам"),
    type_id: Optional[int] = Query(None, description="ID типа документа"),
    direction: Optional[DocDirection] = Query(None, description="Направление (internal/external/etc.)"),
    tag_ids: Optional[list[int]] = Query(None, description="Список ID тегов"),
    date_from: Optional[date] = Query(None, description="Дата создания ОТ"),
    date_to: Optional[date] = Query(None, description="Дата создания ДО"),
    search: Optional[str] = Query(None, description="Строка поиска"),
    sort_by: str = Query("created_at", description="Поле для сортировки"),
    sort_order: str = Query("desc", description="Направление сортировки ('asc' или 'desc')"),
    limit: int = Query(20, ge=1, le=100, description="Размер страницы"),
    offset: int = Query(0, ge=0, description="Смещение выборки"),
    current_user: CurrentUser = Depends(get_current_user),
    service: RegistryService = Depends(get_registry_service)
):
    """Реестр документов с динамической фильтрацией и пагинацией для PyQt6 таблиц"""
    total, items = await service.get_all_paginated(
        user_id=current_user.id,
        user_rights=current_user.rights,
        scope=scope,
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
    return await service.get_user(doc_id, current_user)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
        doc_id: int,
        admin_user: CurrentUser = Depends(RoleChecker([AppRights.admin, AppRights.superadmin])),
        service: DocumentService = Depends(get_doc_service)
):
    """Удаление документа администратором системы"""
    await service.delete(doc_id, admin_user)
    return None


@router.put("/{document_id}/admin-metadata", response_model=DocumentListItem)
async def admin_update_metadata(
        document_id: int,
        payload: AdminMetadataUpdate,
        admin_user: CurrentUser = Depends(RoleChecker([AppRights.admin, AppRights.superadmin])),
        service: DocumentService = Depends(get_doc_service)
):
    """Административное редактирование метаданных в обход ограничений состояний"""
    return await service.admin_update_metadata(document_id, payload, admin_user)

@router.get(
    "/stats/unanswered",
    response_model=list[UnansweredDocumentStat],
    status_code=status.HTTP_200_OK,
    summary="Получить статистику по неотвеченным документам"
)
async def get_unanswered_documents_stats(
    doc_service: DocumentService = Depends(get_doc_service),
    current_user = Depends(get_current_user)
):
    """
    Эндпоинт возвращает список документов:
    - Требующих ответа (`needs_response = True`)
    - На которые еще не поступил ответ (нет записей с `parent_document_id`)
    - С расчетом штрафа/просрочки (дни после дедлайна * 50)
    - С перечнем ответственных ФИО (Получатели и Делегаты)
    """
    return await doc_service.get_unanswered_stats(current_user)




