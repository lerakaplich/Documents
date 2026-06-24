from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from typing import List

from server.app.deps import get_current_user, get_doc_service
from server.app.schemas.user_schemas.employee_dto import CurrentUser

# Импортируем обновленные сервисы СЭД
from server.app.services.documents.document_service import DocumentService

router = APIRouter(prefix="/attachments", tags=["Documents"])

# --- УПРАВЛЕНИЕ АРХИВАМИ С ТИФФАМИ (ВЛОЖЕНИЯ) ---

@router.post("/{document_id}/main", status_code=status.HTTP_200_OK)
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
@router.post("/{document_id}/response", status_code=status.HTTP_200_OK)
async def upload_response_attachments(
        document_id: int,
        files: List[UploadFile] = File(..., description="Файлы отчета об исполнении"),
        current_user: CurrentUser = Depends(get_current_user),
        service: DocumentService = Depends(get_doc_service)
):
    """Загрузить или перезаписать ответное вложение (отчет об исполнении)"""
    await service.save_response_attachments(document_id, files, current_user.id)
    return {"status": "success", "message": "Ответный пакет вложений успешно прикреплен"}


@router.get("/{document_id}/download/{archive_type}")
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