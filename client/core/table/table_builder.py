"""
Модуль настройки таблицы документов - строитель
"""
from PyQt6.QtWidgets import QHeaderView, QAbstractItemView
from PyQt6.QtCore import Qt, QTimer

from client.core.table.managers.column.column_manager import ColumnManager
from client.core.table.managers.row.row_manager import RowManager
from client.core.table.managers.table_data_manager import TableDataManager
from client.core.table.table_facade import TableFacade


class TableBuilder:
    """
    Строитель таблицы - собирает все компоненты вместе.
    Использует паттерн Builder для пошаговой сборки.
    """

    def __init__(self, table_widget, columns_config: dict, doc_type: str = None, view_mode: str = "all"):
        self._table_widget = table_widget
        self._columns_config = columns_config
        self._doc_type = doc_type or "default"
        self._view_mode = view_mode
        self._data_manager = None
        self._updater = None
        self._facade = None

    def setup(self, data_manager: TableDataManager = None, updater=None) -> TableFacade:
        """
        Основная настройка таблицы.
        Возвращает фасад для управления таблицей.
        """
        self._setup_columns()
        self._setup_headers()
        self._setup_appearance()

        # Создаем фасад
        self._facade = TableFacade(
            self._table_widget,
            self._columns_config,
            self._doc_type,
            self._view_mode
        ).build(data_manager, updater)

        return self._facade

    def _setup_columns(self):
        """Установка колонок"""
        columns = list(self._columns_config.values())
        self._table_widget.setColumnCount(len(columns))
        self._table_widget.setHorizontalHeaderLabels(columns)

    def _setup_headers(self):
        """Настройка заголовков"""
        header = self._table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setMinimumSectionSize(60)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(False)

        vertical_header = self._table_widget.verticalHeader()
        vertical_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        vertical_header.setDefaultSectionSize(50)
        vertical_header.setVisible(True)

    def _setup_appearance(self):
        """Настройка внешнего вида"""
        self._table_widget.setShowGrid(False)
        self._table_widget.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self._table_widget.setHorizontalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

    def get_facade(self) -> TableFacade:
        """Получить фасад таблицы"""
        return self._facade