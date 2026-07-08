"""
Управление строками - фасад для менеджеров
"""
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt
from PyQt6.QtWidgets import QHeaderView

from client.core.table.managers.pin_manager import PinManager
from client.core.table.managers.row.row_order_manager import RowOrderManager
from client.core.table.managers.row.row_height_manager import RowHeightManager
from client.core.table.managers.row.row_behavior_manager import RowBehaviorManager


class RowManager(QObject):
    """
    Фасад для управления строками.
    Координирует работу менеджеров.
    """

    pin_changed = pyqtSignal(int, bool)
    order_changed = pyqtSignal(list)

    def __init__(self, table_widget, data_manager, updater, doc_type: str = None):
        super().__init__()
        self._table = table_widget
        self._data_manager = data_manager
        self._updater = updater
        self._doc_type = doc_type or "default"
        self._updating = False

        # Создаем менеджеры
        self._pin_manager = PinManager(self._doc_type)
        self._order_manager = RowOrderManager(self._doc_type)
        self._height_manager = RowHeightManager(self._table, self._doc_type)
        self._behavior_manager = RowBehaviorManager(self._table)

        # Подключаем сигналы
        self._pin_manager.pin_changed.connect(self._on_pin_changed)
        self._pin_manager.pin_changed.connect(self.pin_changed.emit)

        # Подключаем сигналы для порядка строк
        vertical_header = self._table.verticalHeader()
        vertical_header.sectionMoved.connect(self._on_section_moved)
        self._table.model().rowsMoved.connect(self._on_rows_moved)

    def _on_pin_changed(self, document_id: int, is_pinned: bool):
        """Обработчик изменения закрепления"""
        self._apply_pinning()

    def _on_section_moved(self, logical_index, old_visual_index, new_visual_index):
        """Обработчик перемещения секции"""
        if self._updating:
            return
        try:
            documents = self._get_documents_in_order()
            self._save_row_order(documents)
            self.order_changed.emit([doc.get('id') for doc in documents])
        except Exception as e:
            print(f"[RowManager] Error in _on_section_moved: {e}")

    def _on_rows_moved(self, parent, start, end, destination, row):
        """Обработчик перемещения строк"""
        if self._updating:
            return
        try:
            documents = self._get_documents_in_order()
            self._save_row_order(documents)
            self.order_changed.emit([doc.get('id') for doc in documents])
        except Exception as e:
            print(f"[RowManager] Error in _on_rows_moved: {e}")

    def _get_documents_in_order(self) -> list:
        """Получить документы в текущем порядке"""
        documents = []
        reg_col = self.find_reg_number_column()
        if reg_col is None:
            return documents

        for row in range(self._table.rowCount()):
            item = self._table.item(row, reg_col)
            if item:
                doc_data = item.data(Qt.ItemDataRole.UserRole)
                if doc_data:
                    documents.append(doc_data)

        return documents

    def _save_row_order(self, documents: list):
        """Сохранить порядок строк"""
        order_ids = [doc.get('id') for doc in documents if doc.get('id') is not None]
        self._order_manager.save_order(order_ids)

    # ========== PIN ==========

    def get_pin_manager(self) -> PinManager:
        return self._pin_manager

    @property
    def pinned_ids(self) -> list:
        return self._pin_manager.pinned_ids

    def is_pinned(self, document_id: int) -> bool:
        return self._pin_manager.is_pinned(document_id)

    def toggle_pin(self, document_id: int) -> bool:
        self._height_manager.save_heights()
        is_pinned = self._pin_manager.toggle(document_id)
        self._apply_pinning()
        QTimer.singleShot(200, self._height_manager.restore_heights)
        return is_pinned

    # ========== ORDER ==========

    def get_row_order(self) -> list:
        return self._order_manager.get_order()

    def save_row_order(self, document_ids: list):
        self._order_manager.save_order(document_ids)
        self.order_changed.emit(document_ids)

    # ========== HEIGHTS ==========

    def save_heights(self):
        self._height_manager.save_heights()

    def restore_heights(self):
        self._height_manager.restore_heights()

    def schedule_save_heights(self):
        self._height_manager.schedule_save()

    # ========== APPLY ==========

    def apply_pinning(self):
        """Применить закрепление к данным"""
        self._apply_pinning()

    def _apply_pinning(self):
        """Применить закрепление и порядок к данным"""
        documents = self._data_manager.get_documents()
        if not documents:
            return

        pinned_ids = self._pin_manager.pinned_ids

        # Обновляем is_pinned
        for doc in documents:
            doc_id = doc.get('id')
            doc['is_pinned'] = doc_id in pinned_ids

        # Применяем порядок
        sorted_documents = self._order_manager.apply_order(documents, pinned_ids)

        # Обновляем данные
        self._data_manager.update_data(sorted_documents)

        if self._updater:
            self._updater.force_update()

        # Сохраняем порядок
        order_ids = [d.get('id') for d in sorted_documents if d.get('id') is not None]
        self._order_manager.save_order(order_ids)

    # ========== DOC TYPE ==========

    def set_doc_type(self, doc_type: str):
        """Обновить тип документа"""
        if self._doc_type == doc_type:
            return

        self._height_manager.save_heights()
        self._doc_type = doc_type

        self._pin_manager.set_doc_type(doc_type)
        self._order_manager.set_doc_type(doc_type)
        self._height_manager.set_doc_type(doc_type)

        self._apply_pinning()
        QTimer.singleShot(200, self._height_manager.restore_heights)

    # ========== HELPERS ==========

    def find_reg_number_column(self) -> int:
        """Найти колонку 'Номер документа'"""
        for col in range(self._table.columnCount()):
            header_item = self._table.horizontalHeaderItem(col)
            if header_item and header_item.text() == "Номер документа":
                return col
        return None