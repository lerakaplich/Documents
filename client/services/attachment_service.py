# client/services/attachment_service.py
"""
Сервис загрузки вложений к документу.

ВНИМАНИЕ: путь эндпоинта и имя поля формы ("file") — предположение по
стандартной REST-конвенции и структуре таблицы document_attachments
(document_id, file_name, storage_path, file_size, ...). Файл сервера
server/app/api/doc/attachments.py в этой сессии не был доступен для
сверки — перед использованием в проде проверьте реальный путь/имя поля
и поправьте при необходимости.
"""
import logging
from typing import Optional, Dict, Any

from client.core.http_client import HttpClient

logger = logging.getLogger(__name__)


class AttachmentService:
    """Сервис для работы с вложениями документов через API"""

    def __init__(self, http_client: HttpClient):
        self.client = http_client

    def upload_attachment(self, document_id: int, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Загружает файл как вложение к документу document_id.
        Возвращает ответ сервера (созданное вложение) или None при ошибке.
        """
        try:
            return self.client.post_file(
                f"/documents/attachments/{document_id}/attachments",
                file_path,
                field_name="file",
            )
        except Exception as e:
            logger.error(f"❌ upload_attachment(document_id={document_id}): {e}")
            print(f"❌ upload_attachment(document_id={document_id}): {e}")
            return None


# Синглтон — по аналогии с get_doc_type_service
_attachment_service_instance: Optional[AttachmentService] = None


def get_attachment_service(http_client: HttpClient) -> AttachmentService:
    global _attachment_service_instance
    if _attachment_service_instance is None:
        _attachment_service_instance = AttachmentService(http_client)
    return _attachment_service_instance
