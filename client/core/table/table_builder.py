"""
Модуль настройки таблицы документов
"""
from PyQt6.QtWidgets import QHeaderView, QAbstractItemView
from PyQt6.QtCore import Qt

from client.core.sorting.manager import SortingManager
from client.core.table.column_manager import ColumnManager
from client.core.table.row_manager import RowManager
from client.core.table.table_state import TableState


class TableBuilder:
    """Класс для настройки параметров таблицы"""

    def __init__(self, table_widget, columns_config):
        """
        Инициализация настройщика таблицы

        Args:
            table_widget: виджет таблицы
            columns_config: конфигурация колонок
        """
        self.table_widget = table_widget
        self.columns_config = columns_config
        self.column_manager = None
        self.sorting_manager = None
        self.row_manager = None
        self.table_state = TableState()

    def setup(self, data_manager=None, updater=None):
        """Основная настройка таблицы"""
        try:
            self._setup_columns()
            self._setup_headers()
            self._setup_scrolling()
            self._setup_appearance()
            self._set_column_widths()

            # Инициализация менеджеров
            self.column_manager = ColumnManager(self.table_widget, self.columns_config)
            self.sorting_manager = SortingManager(self.table_widget, self.columns_config)

            # Создаем RowManager с зависимостями
            self.row_manager = RowManager(
                self.table_widget,
                data_manager,
                updater
            )

            print("[TableBuilder] Setup completed successfully")
        except Exception as e:
            print(f"[TableBuilder] Error in setup: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _setup_columns(self):
        """Установка колонок"""
        columns = list(self.columns_config.values())
        self.table_widget.setColumnCount(len(columns))
        self.table_widget.setHorizontalHeaderLabels(columns)

    def _setup_headers(self):
        """Настройка заголовков"""
        header = self.table_widget.horizontalHeader()

        # Разрешаем перемещение и изменение размера колонок
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setMinimumSectionSize(60)

        # ВЫРАВНИВАНИЕ ЗАГОЛОВКОВ ПО ЦЕНТРУ
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

        # Включаем сортировку
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(False)

        # Настройка вертикальных заголовков (номера строк)
        vertical_header = self.table_widget.verticalHeader()
        vertical_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        vertical_header.setDefaultSectionSize(50)
        vertical_header.setVisible(True)

    def _setup_scrolling(self):
        """Настройка скроллинга"""
        self.table_widget.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self.table_widget.setHorizontalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )

    def _setup_appearance(self):
        """Настройка внешнего вида"""
        self.table_widget.setShowGrid(False)

    def _set_column_widths(self):
        """Установка начальных размеров колонок"""
        widths = {
            "ID": 50,
            "Прочитано": 80,
            "Номер документа": 130,
            "Тема": 250,
            "Тип": 100,
            "Дата": 90,
            "Статус": 120,
            "Отправители": 150,
            "Получатели": 150,
            "Исполнители": 150,
            "Делегаты": 150,
            "Хэштеги": 180,
            "Комментарии": 200,
            "Вложение": 100,
            "Ответ": 100,
            "Краткое содержание": 200,
            "Срок исполнения": 120,
            "Направление": 120,
            "Входящий номер": 120,
            "Входящая дата": 120,
        }

        for i, col_name in enumerate(self.columns_config.values()):
            if col_name in widths:
                self.table_widget.setColumnWidth(i, widths[col_name])

    def get_column_manager(self):
        """Получение менеджера колонок"""
        return self.column_manager

    def get_sorting_manager(self):
        """Получение менеджера сортировки"""
        return self.sorting_manager

    def get_row_manager(self):
        """Получение менеджера строк"""
        return self.row_manager

    def set_row_manager(self, row_manager):
        """Установка менеджера строк (для внедрения зависимостей)"""
        self.row_manager = row_manager