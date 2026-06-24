"""Управление строками таблицы"""
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtWidgets import QAbstractItemView, QHeaderView

from client.core.settings.settings_manager import SettingsManager


class RowManager(QObject):
    """Управление строками: закрепление, порядок"""

    row_order_changed = pyqtSignal(list)
    pin_changed = pyqtSignal(int, bool)

    def __init__(self, table_widget, data_manager, updater):
        super().__init__()
        self.table_widget = table_widget
        self.data_manager = data_manager
        self.updater = updater
        self.settings = SettingsManager()
        self._updating = False
        self.pinned_ids = self.settings.get_pinned_ids()
        self._setup_row_behavior()

    def _setup_row_behavior(self):
        """Настройка поведения строк"""
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self.table_widget.setDragEnabled(False)
        self.table_widget.setAcceptDrops(False)
        self.table_widget.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)

        vertical_header = self.table_widget.verticalHeader()
        vertical_header.setSectionsMovable(True)
        vertical_header.setDragEnabled(True)
        vertical_header.setDragDropMode(QHeaderView.DragDropMode.InternalMove)
        vertical_header.setDragDropOverwriteMode(False)
        vertical_header.setDefaultSectionSize(30)
        vertical_header.setMinimumSectionSize(20)
        vertical_header.setVisible(True)
        vertical_header.setSectionsClickable(True)

        vertical_header.sectionMoved.connect(self._on_section_moved)
        self.table_widget.model().rowsMoved.connect(self._on_rows_moved)

    def toggle_pin(self, document_id: int):
        """Переключение закрепления"""
        print(f"[RowManager] Toggle pin: {document_id}")

        # Обновляем список
        if document_id in self.pinned_ids:
            self.pinned_ids.remove(document_id)
            is_pinned = False
        else:
            self.pinned_ids.insert(0, document_id)
            is_pinned = True

        # Сохраняем
        self.settings.set_pinned_ids(self.pinned_ids)

        # Применяем
        self._apply_pinning()

        # Сигнал
        self.pin_changed.emit(document_id, is_pinned)

    def is_pinned(self, document_id: int) -> bool:
        """Проверка, закреплен ли документ"""
        return document_id in self.pinned_ids

    def _apply_pinning(self):
        """Применить закрепление"""
        documents = self.data_manager.get_documents()
        if not documents:
            return

        # Разделяем на закрепленные и незакрепленные
        pinned = []
        unpinned = []

        for doc in documents:
            doc_id = doc.get('id')
            if doc_id in self.pinned_ids:
                doc['is_pinned'] = True
                pinned.append(doc)
            else:
                doc['is_pinned'] = False
                unpinned.append(doc)

        # Сортируем закрепленные по порядку
        pinned_sorted = []
        for pid in self.pinned_ids:
            for doc in pinned:
                if doc.get('id') == pid:
                    pinned_sorted.append(doc)
                    break

        # Восстанавливаем порядок незакрепленных
        saved_order = self.settings.get_row_order()
        if saved_order:
            unpinned_dict = {doc.get('id'): doc for doc in unpinned}
            unpinned_sorted = []
            remaining = set(unpinned_dict.keys())

            for doc_id in saved_order:
                if doc_id in remaining and doc_id not in self.pinned_ids:
                    unpinned_sorted.append(unpinned_dict[doc_id])
                    remaining.remove(doc_id)

            for doc_id in remaining:
                if doc_id not in self.pinned_ids:
                    unpinned_sorted.append(unpinned_dict[doc_id])

            unpinned = unpinned_sorted

        # Финальный порядок
        sorted_documents = pinned_sorted + unpinned

        # Обновляем данные
        self.data_manager.update_data(sorted_documents)

        # Обновляем UI
        self.updater.force_update()

        # Сохраняем порядок
        self.settings.set_row_order([d.get('id') for d in sorted_documents])

    def _on_section_moved(self, logical_index, old_visual_index, new_visual_index):
        if self._updating:
            return
        try:
            documents = self._get_documents_in_order()
            self._save_row_order(documents)
            self.row_order_changed.emit([doc.get('id') for doc in documents])
        except Exception as e:
            print(f"[RowManager] Error in _on_section_moved: {e}")

    def _on_rows_moved(self, parent, start, end, destination, row):
        if self._updating:
            return
        try:
            documents = self._get_documents_in_order()
            self._save_row_order(documents)
            self.row_order_changed.emit([doc.get('id') for doc in documents])
        except Exception as e:
            print(f"[RowManager] Error in _on_rows_moved: {e}")

    def _get_documents_in_order(self) -> list:
        """Получение документов в текущем порядке строк"""
        documents = []
        for row in range(self.table_widget.rowCount()):
            item = self.table_widget.item(row, 0)
            if item:
                doc_data = item.data(Qt.ItemDataRole.UserRole)
                if doc_data:
                    documents.append(doc_data)
        return documents

    def _save_row_order(self, documents: list):
        """Сохранение порядка строк в настройки"""
        order_ids = [doc.get('id') for doc in documents]
        self.settings.setValue("row_order", order_ids)
        print(f"[RowManager] Saved row order: {order_ids}")
