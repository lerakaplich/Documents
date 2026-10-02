"""
Контроллер таблицы - координатор всех менеджеров
"""

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal

from client.core.table.table_builder import TableBuilder
from client.core.table.table_icon_updater import TableIconUpdater
from client.core.table.type_columns import disabled_columns


# Столбец → ключи поля типа (серверные и из диалога типа), которые его включают



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
        self._force_rebuild = False

        self._current_doc_type = "default"
        self._current_view_mode = "all"
        self._facade = None
        self._row_manager = None
        self._column_manager = None
        self._icon_updater = TableIconUpdater(self._table)

        self._build_table()

    def _build_table(self):
        """Построить таблицу"""
        columns_config = self._get_columns_config(self._current_doc_type, self._current_view_mode)

        builder = TableBuilder(self._table, columns_config, self._current_doc_type, self._current_view_mode)

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
        self._icon_updater.update_pin_icon(document_id, is_pinned, self._find_reg_number_column())

    def _get_columns_config(self, doc_type: str, view_mode: str) -> dict:
        """Набор столбцов одинаков для всех видов — у типа меняется только видимость
        (см. get_type_hidden_columns). Новые столбцы добавлены в конец, чтобы
        сохранённые ширины и порядок остались на своих местах."""
        names = [
            "ID",
            "Номер документа",
            "Тема",
            "Дата создания",
            "Статус",
            "Отправители",
            "Получатели",
            "Исполнители",
            "Делегаты",
            "Хэштеги",
            "Комментарии",
            "Вложение",
            "Ответ",
            "Краткое содержание",
            "Срок исполнения",
            "Порядковый номер",
            "Направление",
        ]
        return dict(enumerate(names))

    def get_type_hidden_columns(self) -> set:
        """Столбцы, выключенные в настройках текущего типа документа.
        В таблице они остаются (нужны для данных строки), но скрыты и в меню
        «Столбцы» не показываются."""
        if not str(self._current_doc_type).isdigit():
            return set()
        return disabled_columns(self._get_type_fields(int(self._current_doc_type)))

    def _get_type_fields(self, type_id: int) -> dict:
        """Поля типа документа (dict). Кэшируется; неудачный запрос (например,
        тип уже удалён) не кэшируется и даёт пустой набор — показываем все столбцы."""
        if type_id in self._type_fields_cache:
            return self._type_fields_cache[type_id]

        fields = None
        if self._doc_type_service is not None:
            try:
                type_info = self._doc_type_service.get_type(type_id)
                if type_info is not None:
                    fields = type_info.get("fields") or {}
            except Exception as e:
                print(f"[TableController] Не удалось получить поля типа {type_id}: {e}")
        else:
            # Нет http_client (напр. автономный запуск __main__) — тестовые метаданные
            from client.core.data.document_repository import document_repository

            type_info = document_repository.get_document_type_by_id(type_id)
            fields = (type_info or {}).get("fields") or {}

        if fields is None:
            return {}
        self._type_fields_cache[type_id] = fields
        return fields

    def _find_reg_number_column(self) -> int:
        if self._row_manager:
            return self._row_manager.find_reg_number_column()
        return 2

    # ========== ПУБЛИЧНЫЕ МЕТОДЫ ==========

    def load_documents(self, documents: list, doc_type: str | None = None, view_mode: str | None = None):
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
            self._icon_updater.update_all_pin_icons(pinned_ids, self._find_reg_number_column())

        QTimer.singleShot(300, self._restore_heights_after_load)
        self.data_loaded.emit(len(documents))

    def invalidate_type_fields(self):
        """Поля типов изменились: сбрасываем кэш и пересобираем колонки при следующей отрисовке."""
        self._type_fields_cache = {}
        self._force_rebuild = True

    def switch_doc_type(self, doc_type: str, documents: list, view_mode: str | None = None):
        """
        Переключить вид (ключ настроек) с сохранением настроек.
        """
        doc_type = str(doc_type) if doc_type else "default"
        view_mode = view_mode or self._current_view_mode or "all"

        old_doc_type = self._current_doc_type
        old_view_mode = self._current_view_mode

        # Перестраиваем, если сменился вид или изменились поля типов
        if old_doc_type != doc_type or old_view_mode != view_mode or self._force_rebuild:
            if self._facade:
                self._facade.save_state()

            self._current_doc_type = doc_type
            self._current_view_mode = view_mode
            self._force_rebuild = False

            self._build_table()
        else:
            self._current_doc_type = doc_type
            self._current_view_mode = view_mode

        self._data_manager.load_data(documents, doc_type)

        if self._row_manager:
            self._row_manager.apply_pinning()

        if self._row_manager:
            pinned_ids = self._row_manager.pinned_ids
            self._icon_updater.update_all_pin_icons(pinned_ids, self._find_reg_number_column())

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
                    if read_widget and hasattr(read_widget, "set_read_state"):
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

    def change_read_status(self, document_id: int, is_completed: bool):
        from client.services.document_service import DocumentService

        if self._http_client is None:
            return False
        service = DocumentService(self._http_client)
        try:
            service.toggle_completion(document_id, is_completed)
            return True
        except Exception as e:
            print(f"[TableController] change_read_status error: {e}")
            # откатываем чекбокс обратно
            self.update_read_status(document_id, not is_completed)
            return False
