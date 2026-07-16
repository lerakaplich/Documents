"""
Адаптация существующих билдеров для работы с TableCellItem
"""

from PyQt6.QtWidgets import QTableWidgetItem, QWidget, QLabel, QPushButton, QHBoxLayout, QStyleOptionViewItem
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject, QRect
from PyQt6.QtGui import QBrush, QColor, QPainter
from typing import Any, Optional, Callable, Dict, List
from dataclasses import dataclass
from enum import Enum


# ============== Базовые классы ==============

class CellType(Enum):
    """Типы ячеек"""
    TEXT = "text"
    WIDGET = "widget"
    CUSTOM = "custom"


@dataclass
class CellData:
    """Контейнер для данных ячейки"""
    value: Any
    display_text: str = ""
    tooltip: str = ""
    background_color: Optional[QColor] = None
    foreground_color: Optional[QColor] = None
    alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    editable: bool = False
    icon: Optional[Any] = None
    user_data: Any = None

    # Для виджетов
    widget: Optional[QWidget] = None
    widget_builder: Optional[Callable] = None
    widget_args: tuple = ()
    widget_kwargs: dict = None

    def __post_init__(self):
        if self.widget_kwargs is None:
            self.widget_kwargs = {}


class TableCellItem(QTableWidgetItem):
    """
    Кастомный аналог QTableWidgetItem с поддержкой виджетов
    """

    def __init__(self, cell_data: Optional[CellData] = None):
        super().__init__()
        self._cell_data = cell_data or CellData(value="")
        self._widget = None
        self._is_widget_initialized = False
        self._row = -1
        self._document = None
        self._table = None  # Ссылка на таблицу
        self._apply_cell_data()

    def _apply_cell_data(self):
        """Применить настройки из CellData"""
        if self._cell_data.display_text:
            self.setText(self._cell_data.display_text)
        elif self._cell_data.value is not None:
            self.setText(str(self._cell_data.value))

        if self._cell_data.tooltip:
            self.setToolTip(self._cell_data.tooltip)

        if self._cell_data.background_color:
            self.setBackground(QBrush(self._cell_data.background_color))

        if self._cell_data.foreground_color:
            self.setForeground(QBrush(self._cell_data.foreground_color))

        self.setTextAlignment(self._cell_data.alignment)

        if not self._cell_data.editable:
            self.setFlags(self.flags() & ~Qt.ItemFlag.ItemIsEditable)

        if self._cell_data.icon:
            self.setIcon(self._cell_data.icon)

    def set_table(self, table):
        """Установить ссылку на таблицу"""
        self._table = table

    def set_row_data(self, row: int, document: dict):
        """Установить данные строки для создания виджета"""
        self._row = row
        self._document = document

    def get_widget(self) -> Optional[QWidget]:
        """
        Получить виджет для ячейки (создается при первом вызове)
        """
        if self._widget is not None:
            return self._widget

        if self._cell_data.widget:
            self._widget = self._cell_data.widget
            return self._widget

        if self._cell_data.widget_builder and self._row >= 0 and self._document:
            try:
                if self._cell_data.widget_args or self._cell_data.widget_kwargs:
                    self._widget = self._cell_data.widget_builder(
                        self._row, self._document,
                        *self._cell_data.widget_args,
                        **self._cell_data.widget_kwargs
                    )
                else:
                    self._widget = self._cell_data.widget_builder(self._row, self._document)
            except Exception as e:
                error_widget = QLabel(f"Ошибка: {str(e)}")
                error_widget.setStyleSheet("color: red; background-color: transparent;")
                self._widget = error_widget

        return self._widget

    def has_widget(self) -> bool:
        """Есть ли у ячейки виджет"""
        return (self._cell_data.widget is not None or
                self._cell_data.widget_builder is not None)