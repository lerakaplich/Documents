"""
Модуль настройки таблицы документов
"""
from PyQt6.QtWidgets import QHeaderView, QAbstractItemView
from PyQt6.QtCore import Qt, QTimer

from client.core.sorting.manager import SortingManager
from client.core.table.column_manager import ColumnManager
from client.core.table.row_manager import RowManager
from client.core.table.table_state import TableState


class TableBuilder:
    """Класс для настройки параметров таблицы"""

    def __init__(self, table_widget, columns_config, doc_type: str = None, view_mode: str = "all"):
        """
        Инициализация настройщика таблицы

        Args:
            table_widget: виджет таблицы
            columns_config: конфигурация колонок
            doc_type: тип документа для настроек
            view_mode: режим просмотра ("all", "type", "direction")
        """
        self.table_widget = table_widget
        self.columns_config = columns_config
        self.doc_type = doc_type or "default"
        self.view_mode = view_mode or "all"
        self.column_manager = None
        self.sorting_manager = None
        self.row_manager = None
        self.table_state = TableState()

        print(f"[TableBuilder] Initialized for doc_type: {self.doc_type}, view_mode: {self.view_mode}")

    def setup(self, data_manager=None, updater=None):
        """Основная настройка таблицы"""
        try:
            self._setup_columns()
            self._setup_headers()
            self._setup_scrolling()
            self._setup_appearance()
            self._set_column_widths()

            # Инициализация менеджеров с doc_type
            self.column_manager = ColumnManager(self.table_widget, self.columns_config, self.doc_type)
            self.sorting_manager = SortingManager(self.table_widget, self.columns_config)

            # Создаем RowManager с doc_type
            self.row_manager = RowManager(
                self.table_widget,
                data_manager,
                updater,
                self.doc_type
            )

            # Подключаем сохранение высот при изменении
            vertical_header = self.table_widget.verticalHeader()
            vertical_header.sectionResized.connect(self._on_row_height_changed)

            print(f"[TableBuilder] Setup completed for doc_type: {self.doc_type}, view_mode: {self.view_mode}")
            return self

        except Exception as e:
            print(f"[TableBuilder] Error in setup: {e}")
            import traceback
            traceback.print_exc()
            raise

    def update_doc_type(self, doc_type: str):
        """
        Обновить тип документа и перезагрузить настройки.
        Вызывается при смене типа документа.
        """
        doc_type = doc_type or "default"

        if self.doc_type == doc_type:
            return

        # Сохраняем настройки старого типа
        if self.column_manager:
            self.column_manager.save_all()
        if self.row_manager:
            self.row_manager.save_row_heights()

        # Обновляем тип
        self.doc_type = doc_type

        # Обновляем в менеджерах
        if self.column_manager:
            self.column_manager.doc_type = self.doc_type
            self.column_manager.settings.set_current_document_type(self.doc_type)
            # Загружаем настройки нового типа
            self.column_manager.restore_all()

        if self.row_manager:
            self.row_manager.doc_type = self.doc_type
            self.row_manager.pinned_ids = self.row_manager.settings.get_pinned_by_type(self.doc_type)
            # Переприменяем закрепление для нового типа
            self.row_manager._apply_pinning()
            QTimer.singleShot(200, self.row_manager.restore_row_heights)

        print(f"[TableBuilder] Updated doc_type to: {self.doc_type}")

    def _on_row_height_changed(self, logical_index, old_size, new_size):
        """Обработчик изменения высоты строки"""
        if self.row_manager:
            self.row_manager._on_row_height_changed(logical_index, old_size, new_size)

    def _setup_columns(self):
        """Установка колонок"""
        columns = list(self.columns_config.values())
        self.table_widget.setColumnCount(len(columns))
        self.table_widget.setHorizontalHeaderLabels(columns)

    def _setup_headers(self):
        """Настройка заголовков"""
        header = self.table_widget.horizontalHeader()

        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setMinimumSectionSize(60)

        header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

        header.setSectionsClickable(True)
        header.setSortIndicatorShown(False)

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
            "Дата создания": 120,
            "Статус": 120,
            "Направление": 120,
            "Отправители": 150,
            "Получатели": 150,
            "Исполнители": 150,
            "Делегаты": 150,
            "Хэштеги": 180,
            "Комментарии": 200,
            "Вложение": 100,
            "Ответ": 100,
            "Краткое содержание": 200,
            "Срок исполнения": 120
        }

        for i, col_name in enumerate(self.columns_config.values()):
            if col_name in widths:
                self.table_widget.setColumnWidth(i, widths[col_name])

    def get_column_manager(self) -> ColumnManager:
        """Получение менеджера колонок"""
        return self.column_manager

    def get_sorting_manager(self):
        """Получение менеджера сортировки"""
        return self.sorting_manager

    def get_row_manager(self) -> RowManager:
        """Получение менеджера строк"""
        return self.row_manager

    def set_doc_type(self, doc_type: str):
        """Обновить тип документа"""
        self.doc_type = doc_type or "default"
        print(f"[TableBuilder] Updated doc_type to: {self.doc_type}")

    def set_view_mode(self, view_mode: str):
        """Обновить режим просмотра"""
        self.view_mode = view_mode or "all"
        print(f"[TableBuilder] Updated view_mode to: {self.view_mode}")


# table_builder.py

