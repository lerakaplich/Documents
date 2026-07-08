"""
Модуль состояния таблицы - модель состояния UI
"""
from PyQt6.QtCore import QObject, pyqtSignal
from typing import Optional, Dict, Any
from enum import Enum


class SortOrder(Enum):
    """Порядок сортировки"""
    ASCENDING = "ascending"
    DESCENDING = "descending"


class TableState(QObject):
    """Класс для управления состоянием таблицы"""

    state_changed = pyqtSignal()
    selection_changed = pyqtSignal(int, dict)  # row, document
    sort_changed = pyqtSignal(str, str)  # column, order
    filter_changed = pyqtSignal(dict)  # filters

    def __init__(self):
        super().__init__()
        self._selected_row: int = -1
        self._selected_document: Optional[Dict[str, Any]] = None
        self._sort_column: Optional[str] = None
        self._sort_order: Optional[SortOrder] = None
        self._filter_criteria: Dict[str, Any] = {}
        self._current_page: int = 0
        self._page_size: int = 20

    # ========== ВЫБОР ==========

    @property
    def selected_row(self) -> int:
        return self._selected_row

    @selected_row.setter
    def selected_row(self, value: int):
        if self._selected_row != value:
            self._selected_row = value
            self.state_changed.emit()
            self.selection_changed.emit(value, self._selected_document)

    @property
    def selected_document(self) -> Optional[Dict[str, Any]]:
        return self._selected_document

    @selected_document.setter
    def selected_document(self, value: Optional[Dict[str, Any]]):
        if self._selected_document != value:
            self._selected_document = value
            self.state_changed.emit()
            if value:
                self.selection_changed.emit(self._selected_row, value)

    def select_row(self, row: int, document: Optional[Dict[str, Any]] = None):
        """Выбрать строку"""
        self._selected_row = row
        self._selected_document = document
        self.state_changed.emit()
        self.selection_changed.emit(row, document)

    def clear_selection(self):
        """Снять выделение"""
        self._selected_row = -1
        self._selected_document = None
        self.state_changed.emit()

    # ========== СОРТИРОВКА ==========

    @property
    def sort_column(self) -> Optional[str]:
        return self._sort_column

    @sort_column.setter
    def sort_column(self, value: Optional[str]):
        if self._sort_column != value:
            self._sort_column = value
            self.state_changed.emit()
            if value:
                self.sort_changed.emit(value, self._sort_order.value if self._sort_order else "ascending")

    @property
    def sort_order(self) -> Optional[SortOrder]:
        return self._sort_order

    @sort_order.setter
    def sort_order(self, value: Optional[SortOrder]):
        if self._sort_order != value:
            self._sort_order = value
            self.state_changed.emit()
            if value and self._sort_column:
                self.sort_changed.emit(self._sort_column, value.value)

    def set_sort(self, column: str, order: SortOrder = SortOrder.ASCENDING):
        """Установить сортировку"""
        self._sort_column = column
        self._sort_order = order
        self.state_changed.emit()
        self.sort_changed.emit(column, order.value)

    def toggle_sort(self, column: str) -> SortOrder:
        """Переключить сортировку"""
        if self._sort_column == column:
            if self._sort_order == SortOrder.ASCENDING:
                self._sort_order = SortOrder.DESCENDING
            else:
                self._sort_order = SortOrder.ASCENDING
        else:
            self._sort_column = column
            self._sort_order = SortOrder.ASCENDING

        self.state_changed.emit()
        self.sort_changed.emit(column, self._sort_order.value)
        return self._sort_order

    def clear_sort(self):
        """Очистить сортировку"""
        self._sort_column = None
        self._sort_order = None
        self.state_changed.emit()

    # ========== ФИЛЬТРЫ ==========

    def get_filter(self, key: str) -> Optional[Any]:
        """Получить фильтр по ключу"""
        return self._filter_criteria.get(key)

    def set_filter(self, key: str, value: Any):
        """Установить фильтр"""
        self._filter_criteria[key] = value
        self.state_changed.emit()
        self.filter_changed.emit(self._filter_criteria)

    def remove_filter(self, key: str):
        """Удалить фильтр"""
        if key in self._filter_criteria:
            del self._filter_criteria[key]
            self.state_changed.emit()
            self.filter_changed.emit(self._filter_criteria)

    def get_all_filters(self) -> Dict[str, Any]:
        """Получить все фильтры"""
        return self._filter_criteria.copy()

    def clear_filters(self):
        """Очистить все фильтры"""
        self._filter_criteria.clear()
        self.state_changed.emit()
        self.filter_changed.emit({})

    def has_filters(self) -> bool:
        """Есть ли активные фильтры"""
        return bool(self._filter_criteria)

    # ========== ПАГИНАЦИЯ ==========

    @property
    def current_page(self) -> int:
        return self._current_page

    @current_page.setter
    def current_page(self, value: int):
        if self._current_page != value and value >= 0:
            self._current_page = value
            self.state_changed.emit()

    @property
    def page_size(self) -> int:
        return self._page_size

    @page_size.setter
    def page_size(self, value: int):
        if self._page_size != value and value > 0:
            self._page_size = value
            self.state_changed.emit()

    def next_page(self):
        """Следующая страница"""
        self._current_page += 1
        self.state_changed.emit()

    def prev_page(self):
        """Предыдущая страница"""
        if self._current_page > 0:
            self._current_page -= 1
            self.state_changed.emit()

    def reset(self):
        """Сброс состояния"""
        self._selected_row = -1
        self._selected_document = None
        self._sort_column = None
        self._sort_order = None
        self._filter_criteria.clear()
        self._current_page = 0
        self.state_changed.emit()

    def to_dict(self) -> Dict[str, Any]:
        """Сериализация состояния"""
        return {
            "selected_row": self._selected_row,
            "sort_column": self._sort_column,
            "sort_order": self._sort_order.value if self._sort_order else None,
            "filters": self._filter_criteria.copy(),
            "current_page": self._current_page,
            "page_size": self._page_size
        }