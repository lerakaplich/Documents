"""
Контроллер таблицы - координатор всех менеджеров
"""
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtCore import Qt, QSize

from client.core.table.table_builder import TableBuilder
from client.core.table.table_icon_updater import TableIconUpdater
from client.core.utils.icon_manager import icon_manager


class TableController(QObject):
    """
    Контроллер таблицы - координатор.
    """

    pin_status_changed = pyqtSignal(int, bool)
    data_loaded = pyqtSignal(int)

    def __init__(self, table_widget, data_manager, row_renderer, updater, http_client=None):
        super().__init__()
        self._table = table_widget
        self._data_manager = data_manager
        self._row_renderer = row_renderer
        self._updater = updater

        # Реальные доп. поля типа документа (для колонок 20+) — берём через
        # DocTypeService, если есть http_client; иначе (например, автономный
        # запуск модуля из __main__) откатываемся на фейковый document_repository.
        self._http_client = http_client
        self._doc_type_service = None
        if http_client is not None:
            from client.services.doc_type_service import DocTypeService
            self._doc_type_service = DocTypeService(http_client)
        self._type_fields_cache = {}

        self._current_doc_type = "default"
        self._current_view_mode = "all"
        self._facade = None
        self._row_manager = None
        self._column_manager = None
        self._icon_updater = TableIconUpdater(self._table)

        self._build_table()

    def _build_table(self):
        """Построить таблицу"""
        columns_config = self._get_columns_config(
            self._current_doc_type,
            self._current_view_mode
        )

        builder = TableBuilder(
            self._table,
            columns_config,
            self._current_doc_type,
            self._current_view_mode
        )

        self._facade = builder.setup(self._data_manager, self._updater)
        self._row_manager = self._facade.get_row_manager()
        self._column_manager = self._facade.get_column_manager()

        self._data_manager.set_columns_config(columns_config)

        if self._updater:
            self._updater.set_row_manager(self._row_manager)

        if self._row_manager:
            self._row_manager.pin_changed.connect(self._on_pin_changed)

    def _on_pin_changed(self, document_id: int, is_pinned: bool):
        self.pin_status_changed.emit(document_id, is_pinned)
        self._icon_updater.update_pin_icon(
            document_id,
            is_pinned,
            self._find_reg_number_column()
        )

    def _get_columns_config(self, doc_type: str, view_mode: str) -> dict:
        base_columns = {
            0: "ID", 1: "Прочитано", 2: "Номер документа", 3: "Тема",
            5: "Дата создания", 6: "Статус", 8: "Отправители", 9: "Получатели",
            10: "Исполнители", 11: "Делегаты", 12: "Хэштеги", 13: "Комментарии",
            14: "Вложение", 15: "Ответ", 16: "Краткое содержание", 17: "Срок исполнения"
        }

        if view_mode == "all":
            base_columns[4] = "Тип"
            base_columns[7] = "Направление"

        columns_config = dict(sorted(base_columns.items()))

        try:
            type_id = int(doc_type) if doc_type != "default" else None
            if type_id:
                for idx, field in enumerate(self._get_type_fields(type_id), start=20):
                    field_name = field.get("label", field.get("name", f"Поле_{idx}"))
                    columns_config[idx] = field_name
        except (ValueError, TypeError):
            pass

        return columns_config

    def _get_type_fields(self, type_id: int) -> list:
        """Доп. поля типа документа, для колонок 20+. Кэшируется на время жизни контроллера."""
        if type_id in self._type_fields_cache:
            return self._type_fields_cache[type_id]

        fields = []
        if self._doc_type_service is not None:
            try:
                type_info = self._doc_type_service.get_type(type_id)
                fields = (type_info or {}).get("fields") or []
            except Exception as e:
                print(f"[TableController] Не удалось получить поля типа {type_id}: {e}")
                fields = []
        else:
            # Нет http_client (напр. автономный запуск __main__) — тестовые метаданные
            from client.core.data.document_repository import document_repository
            type_info = document_repository.get_document_type_by_id(type_id)
            fields = (type_info or {}).get("fields") or []

        self._type_fields_cache[type_id] = fields
        return fields

    def _find_reg_number_column(self) -> int:
        if self._row_manager:
            return self._row_manager.find_reg_number_column()
        return 2

    # ========== ПУБЛИЧНЫЕ МЕТОДЫ ==========

    def load_documents(self, documents: list, doc_type: str = None, view_mode: str = None):
        """Загрузить документы"""
        doc_type = doc_type or "default"
        view_mode = view_mode or "all"

        old_doc_type = self._current_doc_type
        old_view_mode = self._current_view_mode

        self._current_doc_type = str(doc_type)
        self._current_view_mode = view_mode

        if old_doc_type != self._current_doc_type or old_view_mode != self._current_view_mode:
            # Сохраняем старые настройки (через facade)
            if self._facade:
                self._facade.save_state()
            self._build_table()

        self._data_manager.load_data(documents, doc_type)

        if self._row_manager:
            self._row_manager.apply_pinning()

        if self._row_manager:
            pinned_ids = self._row_manager.pinned_ids
            self._icon_updater.update_all_pin_icons(
                pinned_ids,
                self._find_reg_number_column()
            )

        QTimer.singleShot(300, self._restore_heights_after_load)
        self.data_loaded.emit(len(documents))

    def switch_doc_type(self, doc_type: str, documents: list, view_mode: str = None):
        """
        Переключить тип документа с сохранением настроек.
        """
        doc_type = str(doc_type) if doc_type else "default"
        view_mode = view_mode or self._current_view_mode or "all"

        old_doc_type = self._current_doc_type
        old_view_mode = self._current_view_mode

        # Если тип или режим изменились
        if old_doc_type != doc_type or old_view_mode != view_mode:
            # Сохраняем старые настройки (только через facade, без дублирования)
            if self._facade:
                self._facade.save_state()

            self._current_doc_type = doc_type
            self._current_view_mode = view_mode

            # Перестраиваем таблицу
            self._build_table()
        else:
            # Если тип не изменился, просто обновляем данные
            self._current_doc_type = doc_type
            self._current_view_mode = view_mode

        # Загружаем данные
        self._data_manager.load_data(documents, doc_type)

        if self._row_manager:
            self._row_manager.apply_pinning()

        if self._row_manager:
            pinned_ids = self._row_manager.pinned_ids
            self._icon_updater.update_all_pin_icons(
                pinned_ids,
                self._find_reg_number_column()
            )

        QTimer.singleShot(300, self._restore_heights_after_load)
        self.data_loaded.emit(len(documents))

    def toggle_pin(self, document_id: int):
        if self._row_manager:
            self._row_manager.toggle_pin(document_id)

    def is_pinned(self, document_id: int) -> bool:
        if self._row_manager:
            return self._row_manager.is_pinned(document_id)
        return False

    def get_document_at_row(self, row: int) -> dict:
        if row < 0 or row >= self._table.rowCount():
            return None

        reg_col = self._find_reg_number_column()
        item = self._table.item(row, reg_col)
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def get_selected_document(self):
        current_row = self._table.currentRow()
        if current_row < 0:
            return None
        return self.get_document_at_row(current_row)

    def update_read_status(self, document_id: int, is_read: bool):
        columns_config = self._get_columns_config(self._current_doc_type, self._current_view_mode)
        col_map = {name: idx for idx, name in columns_config.items()}
        read_col = col_map.get("Прочитано")

        if read_col is None:
            return

        reg_col = self._find_reg_number_column()

        for row in range(self._table.rowCount()):
            item = self._table.item(row, reg_col)
            if item:
                doc_data = item.data(Qt.ItemDataRole.UserRole)
                if doc_data and doc_data.get("id") == document_id:
                    read_widget = self._table.cellWidget(row, read_col)
                    if read_widget and hasattr(read_widget, 'set_read_state'):
                        read_widget.set_read_state(is_read)
                    break

    def save_state(self):
        """Сохранить состояние всех менеджеров"""
        if self._facade:
            self._facade.save_state()
        # Убираем дублирующий вызов self._column_manager.save_all()
        # так как facade.save_state() уже сохраняет column_manager

    # ========== PRIVATE ==========

    def _restore_heights_after_load(self):
        if self._column_manager:
            self._column_manager.restore_column_sizes()
        if self._row_manager:
            self._row_manager.restore_heights()