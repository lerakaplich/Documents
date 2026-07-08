from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from server.app.deps import get_attachment_service
from server.app.services.documents.attachment_service import AttachmentService

router = APIRouter(prefix="/attachments", tags=["Documents"])

# --- УПРАВЛЕНИЕ АРХИВАМИ С ТИФФАМИ (ВЛОЖЕНИЯ) ---
@router.post("/{doc_id}/attachments")
async def upload_attachment(
    doc_id: int,
    file: UploadFile = File(...),
    service: AttachmentService = Depends(get_attachment_service)
):
    return await service.add_attachment(doc_id, file)


@router.delete("/{doc_id}/attachments/{attach_id}")
async def remove_attachment(
        doc_id: int,
        attach_id: int,
        service: AttachmentService = Depends(get_attachment_service)):
    count = await service.repo.count_by_doc(doc_id)
    if count <= 1:
        raise HTTPException(400, "Нельзя удалить последнее вложение")

    await service.repo.delete(attach_id)
    return {"message": "Удалено"}