# client/services/attachment_service.py
"""
Сервис работы с вложениями документа через API.

Пути подтверждены реальным роутером server/app/api/doc/attachments.py
(APIRouter(prefix="/attachments"), смонтированным, как и документы,
под общим групповым префиксом "/documents" в main.py — по аналогии с
тем, как router documents.py с prefix="/documents" превращается в
итоговый "/documents/documents"). Отсюда base_path = "/documents/attachments".

ВАЖНО — то, что сервер УМЕЕТ, но клиент пока не использует:
  GET  /{attach_id}/page/{page_num} — отдаёт JPEG-страницу (StreamingResponse),
  а не JSON. Текущий HttpClient._request() всегда делает response.json(),
  поэтому вызвать этот эндпоинт им нельзя как есть — нужен отдельный метод
  вроде HttpClient.get_binary(), которого сейчас нет. Полноценный просмотр
  многостраничных TIFF/PDF вложений (постранично) поэтому не реализован —
  сделан только список вложений и получение числа страниц (get_page_count),
  этого достаточно, чтобы показать пользователю, что вложение есть и сколько
  в нём страниц, без самого превью.

  У ответа get_attachments() поле "preview_url" (см. AttachmentService.
  get_attachments_info на сервере: f"/attachments/{{id}}/preview") ссылается
  на путь, которого в роутере НЕТ (там только /info и /page/{page_num}) —
  это несоответствие на сервере, использовать его как "путь для открытия"
  нельзя.
"""
import logging
from typing import Optional, Dict, Any, List

from client.core.http_client import HttpClient

logger = logging.getLogger(__name__)


class AttachmentService:
    """Сервис для работы с вложениями документов через API"""

    def __init__(self, http_client: HttpClient):
        self.client = http_client
        self.base_path = "/documents/attachments"

    def get_attachments(self, document_id: int) -> List[Dict[str, Any]]:
        """
        GET /documents/attachments/{doc_id}/attachments — список вложений документа.

        Сервер отдаёт [{"id", "file_name", "file_size", "preview_url", "uploaded_at"}, ...].
        Добавляем ключ "name" (алиас file_name), которого ждут билдеры ячеек
        таблицы (AttachmentCellBuilder/ReplyCellBuilder исторически написаны
        под тестовые данные с полем "name").
        """
        try:
            r = self.client.get(f"{self.base_path}/{document_id}/attachments")
            items = r if isinstance(r, list) else []
            for item in items:
                item.setdefault("name", item.get("file_name", "Файл"))
            return items
        except Exception as e:
            logger.error(f"❌ get_attachments(document_id={document_id}): {e}")
            print(f"❌ get_attachments(document_id={document_id}): {e}")
            return []

    def upload_attachment(self, document_id: int, file_path: str) -> Optional[Dict[str, Any]]:
        """POST /documents/attachments/{doc_id}/attachments — загрузить файл как вложение."""
        try:
            return self.client.post_file(
                f"{self.base_path}/{document_id}/attachments",
                file_path,
                field_name="file",
            )
        except Exception as e:
            logger.error(f"❌ upload_attachment(document_id={document_id}): {e}")
            print(f"❌ upload_attachment(document_id={document_id}): {e}")
            return None

    def delete_attachment(self, document_id: int, attachment_id: int) -> bool:
        """DELETE /documents/attachments/{doc_id}/attachments/{attach_id}."""
        try:
            self.client.delete(f"{self.base_path}/{document_id}/attachments/{attachment_id}")
            return True
        except Exception as e:
            logger.error(f"❌ delete_attachment(document_id={document_id}, attachment_id={attachment_id}): {e}")
            print(f"❌ delete_attachment: {e}")
            return False

    def get_page_count(self, attachment_id: int) -> Optional[int]:
        """
        GET /documents/attachments/{attach_id}/info — число страниц вложения
        (для TIFF/сканов). Полный постраничный просмотр не реализован — см.
        предупреждение вверху файла.
        """
        try:
            r = self.client.get(f"{self.base_path}/{attachment_id}/info")
            return r.get("total_pages") if isinstance(r, dict) else None
        except Exception as e:
            logger.error(f"❌ get_page_count(attachment_id={attachment_id}): {e}")
            return None


# Синглтон — по аналогии с get_doc_type_service
_attachment_service_instance: Optional[AttachmentService] = None


def get_attachment_service(http_client: HttpClient) -> AttachmentService:
    global _attachment_service_instance
    if _attachment_service_instance is None:
        _attachment_service_instance = AttachmentService(http_client)
    return _attachment_service_instance