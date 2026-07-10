from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from starlette.responses import StreamingResponse

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


@router.delete("/{doc_id}/attachments/{attach_id}", response_model=None, status_code=204)
async def remove_attachment(
        doc_id: int,
        attach_id: int,
        service: AttachmentService = Depends(get_attachment_service)):
    await service.delete_attachment(doc_id, attach_id)
    return None  # 204 No Content

@router.get("/{doc_id}/attachments")
async def list_attachments(
    doc_id: int,
    service: AttachmentService = Depends(get_attachment_service)
):
    """Получить список всех вложений документа"""
    return await service.get_attachments_info(doc_id)

@router.get("/{attach_id}/info")
async def get_attachment_info(attach_id: int, service: AttachmentService = Depends(get_attachment_service)):
    count = await service.get_page_count(attach_id)
    return {"total_pages": count}

@router.get("/{attach_id}/page/{page_num}")
async def get_page(attach_id: int, page_num: int, service: AttachmentService = Depends(get_attachment_service)):
    stream = await service.get_page_as_stream(attach_id, page_num)
    return StreamingResponse(stream, media_type="image/jpeg")