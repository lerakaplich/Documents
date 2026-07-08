"""
Управление закреплением документов
"""
from PyQt6.QtCore import QObject, pyqtSignal

from client.core.settings.settings_manager import SettingsManager


class PinManager(QObject):
    """
    Менеджер закрепления документов.
    Отвечает только за логику закрепления/открепления.
    """

    pin_changed = pyqtSignal(int, bool)

    def __init__(self, doc_type: str = "default"):
        super().__init__()
        self._doc_type = doc_type or "default"
        self._settings = SettingsManager()
        self._pinned_ids: list = self._load_pinned()

    def _load_pinned(self) -> list:
        """Загрузить закрепленные из настроек"""
        return self._settings.get_pinned_by_type(self._doc_type)

    def _save_pinned(self):
        """Сохранить закрепленные в настройки"""
        self._settings.set_pinned_by_type(self._pinned_ids, self._doc_type)

    @property
    def pinned_ids(self) -> list:
        """Получить список закрепленных ID"""
        return self._pinned_ids.copy()

    def is_pinned(self, document_id: int) -> bool:
        """Проверить, закреплен ли документ"""
        return document_id in self._pinned_ids

    def toggle(self, document_id: int) -> bool:
        """
        Переключить закрепление документа.
        Возвращает новое состояние (True - закреплен)
        """
        if document_id in self._pinned_ids:
            self._pinned_ids.remove(document_id)
            is_pinned = False
        else:
            self._pinned_ids.insert(0, document_id)
            is_pinned = True

        self._save_pinned()
        self.pin_changed.emit(document_id, is_pinned)
        return is_pinned

    def set_doc_type(self, doc_type: str):
        """Обновить тип документа"""
        if self._doc_type == doc_type:
            return
        self._doc_type = doc_type
        self._pinned_ids = self._load_pinned()

    def clear(self):
        """Очистить все закрепления"""
        self._pinned_ids = []
        self._save_pinned()

    def add_pinned(self, document_id: int):
        """Добавить документ в закрепленные"""
        if document_id not in self._pinned_ids:
            self._pinned_ids.insert(0, document_id)
            self._save_pinned()
            self.pin_changed.emit(document_id, True)

    def remove_pinned(self, document_id: int):
        """Удалить документ из закрепленных"""
        if document_id in self._pinned_ids:
            self._pinned_ids.remove(document_id)
            self._save_pinned()
            self.pin_changed.emit(document_id, False)

    def get_pinned_count(self) -> int:
        """Получить количество закрепленных"""
        return len(self._pinned_ids)

    def is_pinned_by_doc_type(self, document_id: int, doc_type: str) -> bool:
        """Проверить закреплен ли документ для конкретного типа"""
        if self._doc_type != doc_type:
            return document_id in self._settings.get_pinned_by_type(doc_type)
        return self.is_pinned(document_id)