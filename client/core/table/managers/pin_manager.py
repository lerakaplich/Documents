"""
Управление закреплением документов.

Закрепы хранятся в БД (персонально для пользователя):
    POST   /documents/workflow/{id}/pin
    DELETE /documents/workflow/{id}/pin
Источник правды — поле is_pinned в списке документов с сервера.
"""

import logging

from PyQt6.QtCore import QObject, pyqtSignal

from client.core.state.app_state import AppState
from client.services.document_service import DocumentService

logger = logging.getLogger(__name__)


class PinManager(QObject):
    """
    Менеджер закрепления документов.
    Локально держит только кэш id закреплённых документов текущей страницы.
    """

    pin_changed = pyqtSignal(int, bool)

    def __init__(self, doc_type: str = "default"):
        super().__init__()
        self._doc_type = doc_type or "default"  # оставлено для совместимости
        self._pinned_ids: list[int] = []
        self._service: DocumentService | None = None

    # ───────── сервис ─────────

    def _doc_service(self) -> DocumentService:
        if self._service is None:
            self._service = DocumentService(AppState().http_client)
        return self._service

    def _send(self, document_id: int, pin: bool) -> bool:
        """Отправить изменение на сервер. True — успех."""
        try:
            if pin:
                self._doc_service().pin_document(document_id)
            else:
                self._doc_service().unpin_document(document_id)
            return True
        except Exception as e:
            logger.error(
                "Не удалось %s документ %s: %s",
                "закрепить" if pin else "открепить",
                document_id,
                e,
            )
            return False

    # ───────── синхронизация с данными сервера ─────────

    def sync_from_documents(self, items: list[dict]) -> None:
        """Вызывать после каждой загрузки страницы документов (до отрисовки строк)."""
        self._pinned_ids = [d["id"] for d in items if d.get("is_pinned")]

    # ───────── публичный API ─────────

    @property
    def pinned_ids(self) -> list:
        return self._pinned_ids.copy()

    def is_pinned(self, document_id: int) -> bool:
        return document_id in self._pinned_ids

    def toggle(self, document_id: int) -> bool:
        """Переключить закрепление. Возвращает актуальное состояние (True — закреплён)."""
        pin = document_id not in self._pinned_ids
        if not self._send(document_id, pin):
            return not pin  # сервер не принял — состояние не меняем
        self._set_local(document_id, pin)
        self.pin_changed.emit(document_id, pin)
        return pin

    def add_pinned(self, document_id: int):
        if document_id not in self._pinned_ids and self._send(document_id, True):
            self._set_local(document_id, True)
            self.pin_changed.emit(document_id, True)

    def remove_pinned(self, document_id: int):
        if document_id in self._pinned_ids and self._send(document_id, False):
            self._set_local(document_id, False)
            self.pin_changed.emit(document_id, False)

    def clear(self):
        """Открепить все документы текущей страницы."""
        for doc_id in self.pinned_ids:
            self.remove_pinned(doc_id)

    def get_pinned_count(self) -> int:
        return len(self._pinned_ids)

    def set_doc_type(self, doc_type: str):
        """Закрепы не зависят от вида — только запоминаем тип."""
        self._doc_type = doc_type or "default"

    def is_pinned_by_doc_type(self, document_id: int, doc_type: str) -> bool:
        return self.is_pinned(document_id)

    # ───────── внутреннее ─────────

    def _set_local(self, document_id: int, pin: bool):
        if pin:
            if document_id not in self._pinned_ids:
                self._pinned_ids.insert(0, document_id)
        elif document_id in self._pinned_ids:
            self._pinned_ids.remove(document_id)