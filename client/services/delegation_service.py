import logging
from typing import Any

logger = logging.getLogger(__name__)


class DelegationService:
    """Перенаправление (делегирование) документов."""

    BASE = "/documents/delegation"  # если роутер подключён с префиксом (например /documents), поправьте здесь

    def __init__(self, http_client):
        self.http = http_client

    def add_delegates(self, document_id: int, target_ids: list[int], message: str = "") -> dict[str, Any]:
        """POST /delegation/{document_id} — назначить сотрудников участниками."""
        logger.info(f"📤 Перенаправление документа {document_id}: {target_ids}")
        payload = {"target_ids": list(target_ids), "message": message or None}
        # Исключения (ApiError) не глотаем: их разбирает вызывающий код
        return self.http.post(f"{self.BASE}/{document_id}", json=payload)

    def remove_delegate(self, document_id: int, employee_id: int) -> dict[str, Any]:
        """DELETE /delegation/{document_id}/{emp_id} — отозвать участника."""
        logger.info(f"🗑 Отзыв участника {employee_id} у документа {document_id}")
        return self.http.delete(f"{self.BASE}/{document_id}/{employee_id}")