# client/services/comment_service.py
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class CommentService:
    """Сервис для работы с комментариями документов."""

    def __init__(self, http_client):
        self.http = http_client

    def get_comments(self, document_id: int) -> List[Dict[str, Any]]:
        """GET /documents/comments/{document_id} — история замечаний с ФИО."""
        try:
            logger.info(f"📥 Запрос комментариев документа {document_id}")
            return self.http.get(f"/documents/comments/{document_id}") or []
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки комментариев: {e}")
            return []

    def add_comment(self, document_id: int, text: str) -> Dict[str, Any]:
        """
        POST /documents/comments/{document_id}/edit — добавить комментарий.
        (Серверный эндпоинт может называться иначе — уточни у бэкенда.)
        """
        try:
            logger.info(f"📤 Отправка комментария к документу {document_id}")
            return self.http.post_form(
                f"/documents/comments/{document_id}/edit",
                data={"text": text},
            )
        except Exception as e:
            logger.error(f"❌ Ошибка отправки комментария: {e}")
            return {}