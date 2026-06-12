from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date

from server.app.database.document_models import DocStatus, DocDirection, AppRights
from server.app.database.session import get_docs_db
from server.app.deps import get_current_user, get_doc_service, get_registry_service, get_review_service, \
    get_comment_service, get_workflow_service
from server.app.repositories.comment_repo import CommentRepository
from server.app.repositories.document_repo import DocumentRepository
from server.app.role_checker import RoleChecker
from server.app.schemas.doc_schemas.document_dto import (
    DocumentListItem, DocumentCreateForm, DocumentDetailRead,
    AdminMetadataUpdate, DocumentPaginationResponse, ToggleCompletionPayload, RedirectHistoryRead
)
from server.app.schemas.user_schemas.employee_dto import CurrentUser

# Импортируем обновленные сервисы СЭД
from server.app.services.documents.document_service import DocumentService
from server.app.services.documents.review_service import DocumentReviewService
from server.app.services.documents.registry_service import DocumentRegistryService
from server.app.services.comment_service import CommentService
from server.app.services.documents.workflow_service import DocumentWorkflowService

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


# --- ЖИЗНЕННЫЙ ЦИКЛ, СОГЛАСОВАНИЕ И ЗАМЕЧАНИЯ ---

@router.post("/{document_id}/edit-revision", response_model=dict)
async def make_document_revisions(
        document_id: int,
        text: str = Form(..., description="Текст вносимых правок/замечаний"),
        current_user: CurrentUser = Depends(get_current_user),
        service: DocumentReviewService = Depends(get_review_service)
):
    """Внесение правок согласующим лицом без вынесения итогового решения"""
    await service.make_revisions(document_id=document_id, user_id=current_user.id, text=text)
    return {"status": "success", "message": "Правки успешно добавлены в историю документа"}


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


@router.get("/{document_id}/comments", response_model=List[dict])
async def get_document_comments_history(
        document_id: int,
        current_user: CurrentUser = Depends(get_current_user),
        comment_svc: CommentService = Depends(get_comment_service)
):
    """Получить полную историю замечаний к документу с расшифрованными ФИО авторов"""
    return await comment_svc.get_document_comments_with_authors(document_id)


@router.post("/{document_id}/toggle-completion", status_code=status.HTTP_200_OK)
async def toggle_completion(
        document_id: int,
        payload: ToggleCompletionPayload,
        current_user: CurrentUser = Depends(get_current_user),
        service: DocumentReviewService = Depends(get_review_service)
):
    """Переключение документа между вкладками 'В работе' и 'Архив'"""
    await service.toggle_complete(document_id, current_user.id, payload.is_completed)
    return {"status": "success", "message": "Статус отображения изменен"}


# --- УПРАВЛЕНИЕ АРХИВАМИ С ТИФФАМИ (ВЛОЖЕНИЯ) ---

@router.post("/{document_id}/attachments/main", status_code=status.HTTP_200_OK)
async def update_main_attachments(
        document_id: int,
        files: List[UploadFile] = File(..., description="Полный список файлов"),
        current_user: CurrentUser = Depends(get_current_user),
        service: DocumentService = Depends(get_doc_service)
):
    """Загрузка основного пакета документов"""
    await service.save_main_attachments(document_id, files, current_user.id)
    return {"status": "success", "message": "Основной пакет вложений успешно обновлен"}


# ИСПРАВЛЕНО: Убран дубликат метода загрузки ответных вложений
@router.post("/{document_id}/attachments/response", status_code=status.HTTP_200_OK)
async def upload_response_attachments(
        document_id: int,
        files: List[UploadFile] = File(..., description="Файлы отчета об исполнении"),
        current_user: CurrentUser = Depends(get_current_user),
        service: DocumentService = Depends(get_doc_service)
):
    """Загрузить или перезаписать ответное вложение (отчет об исполнении)"""
    await service.save_response_attachments(document_id, files, current_user.id)
    return {"status": "success", "message": "Ответный пакет вложений успешно прикреплен"}


@router.get("/{document_id}/attachments/download/{archive_type}")
async def download_attachments_archive(
        document_id: int,
        archive_type: str,
        current_user: CurrentUser = Depends(get_current_user),
        service: DocumentService = Depends(get_doc_service)
):
    """Скачивание ZIP-архива файлов документа (основной или ответный пакет)"""
    file_path = await service.get_attachment_path(document_id, archive_type)
    if not file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запрошенный архив вложений отсутствует")

    return FileResponse(path=file_path, filename=f"doc_{document_id}_{archive_type}.zip", media_type="application/zip")


# --- ЭНДПОИНТЫ ДЕЛЕГИРОВАНИЯ ---

@router.post("/{document_id}/delegates", status_code=status.HTTP_201_CREATED)
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

@router.delete("/{document_id}/delegates/{emp_id}")
async def remove_delegate(
        document_id: int,
        emp_id: int,
        current_user: CurrentUser = Depends(get_current_user),
        service: DocumentWorkflowService = Depends(get_workflow_service)
):
    """Отозвать права участника (только если есть права на управление)"""
    await service.remove_delegate(document_id, current_user.id, emp_id)
    return {"status": "success", "message": "Сотрудник удален из списка участников"}

@router.get("/{document_id}/redirect-history", response_model=List[RedirectHistoryRead])
async def get_redirect_history(
        document_id: int,
        current_user: CurrentUser = Depends(get_current_user),
        service: DocumentWorkflowService = Depends(get_workflow_service)
):
    """История движений документа"""
    return await service.get_history(document_id)