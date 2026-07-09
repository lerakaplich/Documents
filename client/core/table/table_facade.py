"""
Фасад для работы с таблицей - единая точка входа
"""
from PyQt6.QtCore import QObject
from PyQt6.QtCore import QTimer

from client.core.table.managers.column.column_manager import ColumnManager
from client.core.table.managers.row.row_manager import RowManager
from client.core.table.managers.table_data_manager import TableDataManager


class TableFacade(QObject):
    """
    Фасад для таблицы - упрощает взаимодействие между компонентами.
    Координирует работу менеджеров и предоставляет простой API.
    """

    def __init__(self, table_widget, columns_config, doc_type: str = "default", view_mode: str = "all"):
        super().__init__()
        self._table_widget = table_widget
        self._columns_config = columns_config
        self._doc_type = doc_type
        self._view_mode = view_mode

        # Инициализируем менеджеры
        self.data_manager = None
        self.column_manager = ColumnManager(table_widget, columns_config, doc_type)
        self.row_manager = None
        self._initialized = False

    def build(self, data_manager: TableDataManager = None, updater=None) -> 'TableFacade':
        """Собрать таблицу со всеми менеджерами"""
        self.data_manager = data_manager
        self.row_manager = RowManager(
            self._table_widget,
            data_manager,
            updater,
            self._doc_type
        )
        self._initialized = True
        return self

    def load_documents(self, documents: list, doc_type: str = None, view_mode: str = None):
        """Загрузить документы с обновлением типа если нужно"""
        if not self._initialized:
            raise RuntimeError("TableFacade не инициализирован. Вызовите build() сначала.")

        doc_type = doc_type or self._doc_type
        view_mode = view_mode or self._view_mode

        # Обновляем тип если изменился
        if doc_type != self._doc_type:
            self._update_doc_type(doc_type)

        # Обновляем режим просмотра если изменился
        if view_mode != self._view_mode:
            self._update_view_mode(view_mode)

        # Загружаем данные
        if self.data_manager:
            self.data_manager.load_data(documents, doc_type)

        # Применяем закрепление
        if self.row_manager:
            self.row_manager.apply_pinning()
            self._update_pin_icons()

        # Восстанавливаем высоты
        QTimer.singleShot(300, self._restore_heights)

    def _update_doc_type(self, doc_type: str):
        """Обновить тип документа во всех менеджерах"""
        self._doc_type = doc_type

        if self.column_manager:
            self.column_manager.set_doc_type(doc_type)

        if self.row_manager:
            self.row_manager.set_doc_type(doc_type)

    def _update_view_mode(self, view_mode: str):
        """Обновить режим просмотра"""
        self._view_mode = view_mode

    def _restore_heights(self):
        """Восстановить высоты строк"""
        if self.row_manager:
            self.row_manager.restore_heights()

    def _update_pin_icons(self):
        """Обновить иконки закрепления"""
        pass

    def save_state(self):
        """Сохранить состояние всех менеджеров"""
        if self.column_manager:
            self.column_manager.save_all()
        if self.row_manager:
            self.row_manager.save_heights()

    def restore_state(self):
        """Восстановить состояние всех менеджеров"""
        if self.column_manager:
            self.column_manager.restore_all()
        if self.row_manager:
            self.row_manager.restore_heights()

    def toggle_pin(self, doc_id: int):
        """Переключить закрепление документа"""
        if self.row_manager:
            self.row_manager.toggle_pin(doc_id)

    def is_pinned(self, doc_id: int) -> bool:
        """Проверить закреплен ли документ"""
        return self.row_manager.is_pinned(doc_id) if self.row_manager else False

    def get_column_manager(self) -> ColumnManager:
        return self.column_manager

    def get_row_manager(self) -> RowManager:
        return self.row_manager

    def get_data_manager(self) -> TableDataManager:
        return self.data_manager

    @property
    def doc_type(self) -> str:
        return self._doc_type

    @property
    def view_mode(self) -> str:
        return self._view_mode

    @property
    def columns_config(self) -> dict:
        return self._columns_config

    @columns_config.setter
    def columns_config(self, value: dict):
        self._columns_config = value
        if self.column_manager:
            self.column_manager.columns_config = value