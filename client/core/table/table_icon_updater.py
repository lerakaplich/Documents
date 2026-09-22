"""
Обновление иконок в таблице
"""
from PyQt6.QtCore import QObject, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize

from client.core.utils.icon_manager import icon_manager


class TableIconUpdater(QObject):
    """
    Обновление иконок в таблице (закрепление, статусы и т.д.)
    """

    def __init__(self, table_widget):
        super().__init__()
        self._table = table_widget

    def update_pin_icon(self, document_id: int, is_pinned: bool, reg_col: int = None):
        """Обновить иконку закрепления для документа"""
        if reg_col is None:
            reg_col = self._find_reg_number_column()
            if reg_col is None:
                return

        for row in range(self._table.rowCount()):
            item = self._table.item(row, reg_col)
            if item:
                doc_data = item.data(Qt.ItemDataRole.UserRole)
                if doc_data and doc_data.get("id") == document_id:
                    doc_data["is_pinned"] = is_pinned
                    item.setData(Qt.ItemDataRole.UserRole, doc_data)
                    if is_pinned:
                        pin_icon = icon_manager.get_icon('pin', QSize(22, 22))
                        item.setIcon(pin_icon)
                    else:
                        item.setIcon(QIcon())
                    break

    def update_all_pin_icons(self, pinned_ids: list, reg_col: int = None):
        """Обновить все иконки закрепления"""
        if reg_col is None:
            reg_col = self._find_reg_number_column()
            if reg_col is None:
                return

        for row in range(self._table.rowCount()):
            item = self._table.item(row, reg_col)
            if item:
                doc_data = item.data(Qt.ItemDataRole.UserRole)
                if doc_data:
                    doc_id = doc_data.get("id")
                    is_pinned = doc_id in pinned_ids
                    doc_data["is_pinned"] = is_pinned
                    item.setData(Qt.ItemDataRole.UserRole, doc_data)

                    if is_pinned:
                        pin_icon = icon_manager.get_icon('pin', QSize(22, 22))
                        item.setIcon(pin_icon)
                    else:
                        item.setIcon(QIcon())

    def _find_reg_number_column(self) -> int:
        """Найти колонку 'Номер документа'"""
        for col in range(self._table.columnCount()):
            header_item = self._table.horizontalHeaderItem(col)
            if header_item and header_item.text() == "Номер документа":
                return col
        return None