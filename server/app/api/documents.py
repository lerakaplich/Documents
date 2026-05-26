from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date

from server.app.database.session import get_docs_db
from server.app.database.models import AppRights, DocStatus, DocDirection
from server.app.api.deps import get_current_user, RoleChecker
from server.app.schemas.doc_schemas.document_dto import DocumentToggleComplete, DocumentListItem, DocumentCreateForm, \
    DocumentDetailRead, AdminMetadataUpdate, ReviewDocumentPayload, ToggleCompletionPayload
from server.app.schemas.user_schemas.employee_dto import CurrentUser

# Импортируем наш сервис!
from server.app.services.documents import DocumentService
from fastapi.responses import FileResponse # <- Добавляем сюда

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/", response_model=DocumentListItem, status_code=status.HTTP_201_CREATED)
async def create_document(
        payload: DocumentCreateForm,
        current_user: CurrentUser = Depends(get_current_user),
        db_docs: AsyncSession = Depends(get_docs_db)
):
    service = DocumentService(db_docs)
    return await service.create(payload, current_user.id)


@router.get("/", response_model=List[DocumentListItem])
async def get_documents(
    scope: str = "my",
    is_completed: Optional[bool] = None,
    status_filters: Optional[List[DocStatus]] = Query(None),
    type_id: Optional[int] = None,
    direction: Optional[DocDirection] = None,
    tag_ids: Optional[List[int]] = Query(None), # Передача списком: ?tag_ids=1&tag_ids=2
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",  # Добавляем: "asc" или "desc"
    current_user: CurrentUser = Depends(get_current_user),
    db_docs: AsyncSession = Depends(get_docs_db)
):
    """
    Универсальный реестр документов с поддержкой сложных комбинаций фильтров
    (для тематических вкладок интерфейса PyQt6).
    """
    service = DocumentService(db_docs)
    return await service.get_all(
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
        sort_order=sort_order
    )


@router.get("/{doc_id}", response_model=DocumentDetailRead)
async def get_document_by_id(
        doc_id: int,
        current_user: CurrentUser = Depends(get_current_user),
        db_docs: AsyncSession = Depends(get_docs_db)
):
    service = DocumentService(db_docs)
    return await service.get_by_id(doc_id, current_user.id, current_user.rights)


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
        doc_id: int,
        admin_user: CurrentUser = Depends(RoleChecker([AppRights.admin, AppRights.superadmin])),
        db_docs: AsyncSession = Depends(get_docs_db)
):
    service = DocumentService(db_docs)
    await service.delete(doc_id)
    return None

# ============================================================================
# 1. АДМИНИСТРАТИВНОЕ РЕДАКТИРОВАНИЕ
# ============================================================================

@router.put("/{document_id}/admin-metadata", response_model=DocumentListItem)
async def admin_update_metadata(
    document_id: int,
    payload: AdminMetadataUpdate,
    current_user: CurrentUser = Depends(get_current_user), # Используем базовую зависимость
    db_docs: AsyncSession = Depends(get_docs_db)
):
    """
    [Админ-панель] Прямое принудительное редактирование метаданных карточки
    в обход стандартных кругов согласования. Доступно только admin и superadmin.
    """
    # Жесткая проверка прав «на лету»
    if current_user.rights not in [AppRights.admin, AppRights.superadmin]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения данной операции. Требуются права Администратора."
        )

    service = DocumentService(db_docs)
    return await service.admin_update_metadata(document_id, payload)


# ============================================================================
# 2. УТВЕРЖДЕНИЕ / СОГЛАСОВАНИЕ
# ============================================================================

@router.post("/{document_id}/review", status_code=status.HTTP_200_OK)
async def review_document(
        document_id: int,
        payload: ReviewDocumentPayload,
        current_user: CurrentUser = Depends(get_current_user),
        db_docs: AsyncSession = Depends(get_docs_db)
):
    """
    Принять решение по документу (Утвердить / Отклонить).
    Меняет флаг согласования у текущего сотрудника и пересчитывает общий статус документа.
    """
    service = DocumentService(db_docs)
    await service.process_review(document_id, current_user.id, payload.approved, payload.comment)
    return {"status": "success", "message": "Решение по документу успешно зафиксировано"}


# ============================================================================
# 3. ОТМЕТКА О ВЫПОЛНЕНИИ (В РАБОТЕ / АРХИВ)
# ============================================================================

@router.post("/{document_id}/toggle-completion", status_code=status.HTTP_200_OK)
async def toggle_completion(
        document_id: int,
        payload: ToggleCompletionPayload,
        current_user: CurrentUser = Depends(get_current_user),
        db_docs: AsyncSession = Depends(get_docs_db)
):
    """
    Переключить состояние документа для текущего пользователя (В работе <=> В архиве).
    Влияет на фильтрацию по умолчанию на клиенте.
    """
    service = DocumentService(db_docs)
    await service.toggle_completion(document_id, current_user.id, payload.is_completed)
    return {"status": "success", "message": "Статус отображения изменен"}


# ============================================================================
# 4 & 5. УПРАВЛЕНИЕ ПАКЕТНЫМИ ВЛОЖЕНИЯМИ (АРХИВЫ С TIFF)
# ============================================================================

@router.post("/{document_id}/attachments/main", status_code=status.HTTP_200_OK)
async def update_main_attachments(
        document_id: int,
        files: List[UploadFile] = File(..., description="Полный список актуальных файлов вложения"),
        current_user: CurrentUser = Depends(get_current_user),
        db_docs: AsyncSession = Depends(get_docs_db)
):
    """
    Загрузить или обновить пакет основных вложений.
    Принимает файлы, конвертирует сканы в TIFF, упаковывает в единый ZIP и обновляет file_path.
    """
    service = DocumentService(db_docs)
    await service.save_main_attachments(document_id, files, current_user.id)
    return {"status": "success", "message": "Основной пакет вложений успешно обновлен"}


@router.post("/{document_id}/attachments/response", status_code=status.HTTP_200_OK)
async def upload_response_attachments(
        document_id: int,
        files: List[UploadFile] = File(..., description="Файлы отчета об исполнении"),
        current_user: CurrentUser = Depends(get_current_user),
        db_docs: AsyncSession = Depends(get_docs_db)
):
    """
    Загрузить или перезаписать ответное вложение (отчет о выполнении).
    Файлы конвертируются, пакуются в ZIP и путь пишется в response_file_path.
    """
    service = DocumentService(db_docs)
    await service.save_response_attachments(document_id, files, current_user.id)
    return {"status": "success", "message": "Ответный пакет вложений успешно прикреплен"}


@router.get("/{document_id}/attachments/download/{archive_type}")
async def download_attachments_archive(
        document_id: int,
        archive_type: str,  # "main" или "response"
        current_user: CurrentUser = Depends(get_current_user),
        db_docs: AsyncSession = Depends(get_docs_db)
):
    """
    Скачать ZIP-архив с вложениями (основными или ответными) для распаковки
    и просмотра файлов в интерфейсе PyQt6.
    """
    service = DocumentService(db_docs)
    file_path = await service.get_attachment_path(document_id, archive_type)

    if not file_path:
        raise HTTPException(status_code=404, detail="Запрошенный архив вложений отсутствует")

    return FileResponse(path=file_path, filename=f"doc_{document_id}_{archive_type}.zip", media_type="application/zip")


# ============================================================================
# 6. ПЕРЕНАПРАВЛЕНИЕ / ДЕЛЕГИРОВАНИЕ
# ============================================================================

@router.post("/{document_id}/redirect", status_code=status.HTTP_201_CREATED)
async def redirect_document(
        document_id: int,
        to_employee_id: int = Form(..., description="ID сотрудника, которому пересылается документ"),
        message: Optional[str] = Form(None, description="Текст резолюции / поручения"),
        current_user: CurrentUser = Depends(get_current_user),
        db_docs: AsyncSession = Depends(get_docs_db)
):
    """
    Перенаправить документ на другого сотрудника. СЭД создает запись в истории
    перенаправлений и добавляет сотрудника в матрицу участников (роль delegate/executor).
    """
    service = DocumentService(db_docs)
    await service.redirect_document(document_id, current_user.id, to_employee_id, message)
    return {"status": "success", "message": f"Документ успешно перенаправлен сотруднику {to_employee_id}"}


# ============================================================================
# 7. ВНЕСЕНИЕ ПРАВОК И СБРОС КРУГА СОГЛАСОВАНИЯ
# ============================================================================

@router.post("/{document_id}/edit-revision", response_model=DocumentListItem)
async def make_document_revisions(
        document_id: int,
        title: Optional[str] = Form(None, description="Обновленное название"),
        about: Optional[str] = Form(None, description="Обновленная аннотация"),
        new_files: Optional[List[UploadFile]] = File(None, description="Новый пакет файлов, если они менялись"),
        current_user: CurrentUser = Depends(get_current_user),
        db_docs: AsyncSession = Depends(get_docs_db)
):
    """
    Внести правки в документ (новая ревизия). Сбрасывает все выставленные
    ранее статусы `is_approved` у получателей обратно в FALSE и возвращает на круг согласования.
    """
    service = DocumentService(db_docs)
    return await service.make_revisions(
        document_id=document_id,
        user_id=current_user.id,
        title=title,
        about=about,
        new_files=new_files
    )