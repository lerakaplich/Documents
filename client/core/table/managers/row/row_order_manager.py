"""
Управление порядком строк
"""
from PyQt6.QtCore import QObject, pyqtSignal

from client.core.settings.settings_manager import SettingsManager


class RowOrderManager(QObject):
    """
    Управление порядком строк.
    Отвечает только за сортировку и порядок.
    """

    order_changed = pyqtSignal(list)

    def __init__(self, doc_type: str = "default"):
        super().__init__()
        self._doc_type = doc_type or "default"
        self._settings = SettingsManager()

    def get_order(self) -> list:
        """Получить сохраненный порядок"""
        return self._settings.get_row_order_by_type(self._doc_type)

    def save_order(self, document_ids: list):
        """Сохранить порядок"""
        self._settings.set_row_order_by_type(document_ids, self._doc_type)

    def set_doc_type(self, doc_type: str):
        """Обновить тип документа"""
        self._doc_type = doc_type or "default"

    def apply_order(self, documents: list, pinned_ids: list) -> list:
        """
        Применить порядок к документам.
        Сначала закрепленные, потом остальные в сохраненном порядке.
        """
        if not documents:
            return documents

        # Разделяем на закрепленные и незакрепленные
        pinned = [doc for doc in documents if doc.get('id') in pinned_ids]
        unpinned = [doc for doc in documents if doc.get('id') not in pinned_ids]

        # Сортируем закрепленные по порядку
        pinned_dict = {doc.get('id'): doc for doc in pinned}
        pinned_sorted = [pinned_dict[pid] for pid in pinned_ids if pid in pinned_dict]

        # Восстанавливаем порядок незакрепленных
        saved_order = self.get_order()
        if saved_order:
            unpinned_dict = {doc.get('id'): doc for doc in unpinned}
            unpinned_sorted = []
            remaining = set(unpinned_dict.keys())

            for doc_id in saved_order:
                if doc_id in remaining and doc_id not in pinned_ids:
                    unpinned_sorted.append(unpinned_dict[doc_id])
                    remaining.remove(doc_id)

            for doc_id in remaining:
                if doc_id not in pinned_ids:
                    unpinned_sorted.append(unpinned_dict[doc_id])

            unpinned = unpinned_sorted

        return pinned_sorted + unpinned