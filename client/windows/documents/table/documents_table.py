"""
Основной модуль таблицы документов - ТОЛЬКО UI
"""
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QWidget, QTableWidget, QApplication,
                             QVBoxLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize, QTimer

from client.core.data.document_data import DocumentDataConfig
from client.core.table.table_builder import TableBuilder
from client.core.table.table_data_manager import TableDataManager
from client.core.table.table_updater import TableUpdater
from client.core.utils.icon_manager import icon_manager
from client.windows.documents.table.builders.row_filler import RowFiller
from client.windows.documents.table.styles import TableStyles
from client.windows.documents.table.context_menu import ContextMenu


class DocumentsTable(QWidget):
    """
    Таблица документов - ТОЛЬКО UI компонент.
    """

    document_action_triggered = pyqtSignal(str, dict)
    read_status_changed = pyqtSignal(int, bool)
    attachment_added = pyqtSignal(int, str)
    attachment_opened = pyqtSignal(int, str)
    reply_attachment_added = pyqtSignal(int, str)
    pin_status_changed = pyqtSignal(int, bool)
    data_loaded = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._current_doc_type = "default"
        self._current_view_mode = "all"  # "all", "type", "direction"
        self._restore_timer = None
        self._is_loading = False  # Флаг загрузки

        self._init_ui()
        self._init_components()
        self._connect_signals()

    def _init_ui(self):
        """Инициализация пользовательского интерфейса"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tableWidget = QTableWidget()
        self.tableWidget.setObjectName("tableWidget")
        self.tableWidget.setAlternatingRowColors(True)

        layout.addWidget(self.tableWidget)

        self.setStyleSheet(TableStyles.get_main_style())
        self.tableWidget.setStyleSheet(TableStyles.get_table_style())

    def _init_components(self):
        """Инициализация компонентов"""
        self.config = DocumentDataConfig()

        self.row_filler = RowFiller(self.tableWidget, self.config, self)
        self.data_manager = TableDataManager(self.tableWidget, self.row_filler)
        self.updater = TableUpdater(self.tableWidget)

        # Создаем TableBuilder с doc_type и view_mode
        self._rebuild_table_builder("default", "all")

        self.context_menu_manager = ContextMenu(self)

    # documents_table.py

    def _rebuild_table_builder(self, doc_type: str = None, view_mode: str = None):
        """
        Пересоздать TableBuilder с новым типом документа.
        """
        if doc_type is None:
            doc_type = "default"
        if view_mode is None:
            view_mode = "all"

        self._current_doc_type = str(doc_type)
        self._current_view_mode = view_mode

        # Получаем конфигурацию колонок
        columns_config = self._get_columns_config(self._current_doc_type, self._current_view_mode)

        # ЕСЛИ TableBuilder уже существует - обновляем его
        if hasattr(self, 'table_builder') and self.table_builder:
            # Обновляем конфигурацию колонок
            self.table_builder.columns_config = columns_config
            # Обновляем тип
            self.table_builder.update_doc_type(self._current_doc_type)
            # Обновляем режим просмотра
            self.table_builder.view_mode = self._current_view_mode
            # Переустанавливаем колонки
            self._setup_columns(columns_config)
        else:
            # Создаем новый
            self.table_builder = TableBuilder(
                self.tableWidget,
                columns_config,
                self._current_doc_type,
                self._current_view_mode
            )
            self.table_builder.setup(self.data_manager, self.updater)

        # Получаем RowManager
        self.row_manager = self.table_builder.get_row_manager()
        if self.updater:
            self.updater.set_row_manager(self.row_manager)

        print(
            f"[DocumentsTable] Rebuilt TableBuilder for doc_type: {self._current_doc_type}, view_mode: {self._current_view_mode}")

    def _setup_columns(self, columns_config: dict):
        """Переустановка колонок при смене типа"""
        columns = list(columns_config.values())
        self.tableWidget.setColumnCount(len(columns))
        self.tableWidget.setHorizontalHeaderLabels(columns)


    def _get_columns_config(self, doc_type: str, view_mode: str) -> dict:
        """
        Получить конфигурацию колонок для типа документа и режима просмотра.

        Args:
            doc_type: тип документа
            view_mode: режим просмотра ("all", "type", "direction")
        """
        # Базовые колонки - все кроме "Направление" и "Тип"
        base_columns = {
            0: "ID",
            1: "Прочитано",
            2: "Номер документа",
            3: "Тема",
            # 4: "Тип" - будет добавлен только в режиме "all"
            5: "Дата создания",
            6: "Статус",
            # 7: "Направление" - будет добавлен только в режиме "all"
            8: "Отправители",
            9: "Получатели",
            10: "Исполнители",
            11: "Делегаты",
            12: "Хэштеги",
            13: "Комментарии",
            14: "Вложение",
            15: "Ответ",
            16: "Краткое содержание",
            17: "Срок исполнения"
        }

        # В режиме "all" добавляем колонки "Тип" и "Направление"
        if view_mode == "all":
            base_columns[4] = "Тип"
            base_columns[7] = "Направление"
        # Сортируем по индексу
        columns_config = dict(sorted(base_columns.items()))

        # Если есть дополнительные поля из типа документа - добавляем их
        try:
            type_id = int(doc_type) if doc_type != "default" else None
            if type_id:
                from client.core.data.document_repository import document_repository
                type_info = document_repository.get_document_type_by_id(type_id)
                if type_info and type_info.get("fields"):
                    fields = type_info["fields"]
                    for idx, field in enumerate(fields, start=20):
                        field_name = field.get("label", field.get("name", f"Поле_{idx}"))
                        columns_config[idx] = field_name
        except (ValueError, TypeError):
            pass

        return columns_config

    def _get_reg_number_column(self) -> int:
        """Получить индекс колонки 'Номер документа'"""
        # Используем актуальную конфигурацию
        columns_config = self._get_columns_config(self._current_doc_type, self._current_view_mode)
        col_map = {name: idx for idx, name in columns_config.items()}
        return col_map.get("Номер документа", 2)

    def _get_document_from_row(self, row: int) -> dict:
        """Получить документ из строки по индексу"""
        if row < 0 or row >= self.tableWidget.rowCount():
            return None

        reg_number_col = self._get_reg_number_column()
        item = self.tableWidget.item(row, reg_number_col)
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def _connect_signals(self):
        """Подключение сигналов"""
        self.tableWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tableWidget.customContextMenuRequested.connect(self.show_context_menu)

        self.context_menu_manager.redirect_requested.connect(
            lambda doc: self.document_action_triggered.emit("redirect", doc)
        )
        self.context_menu_manager.comment_requested.connect(
            lambda doc: self.document_action_triggered.emit("comment", doc)
        )
        self.context_menu_manager.history_requested.connect(
            lambda doc: self.document_action_triggered.emit("history", doc)
        )
        self.context_menu_manager.edit_requested.connect(
            lambda doc: self.document_action_triggered.emit("edit", doc)
        )
        self.context_menu_manager.read_status_requested.connect(
            lambda doc, status: self.document_action_triggered.emit(
                "read_status", {**doc, "is_read": status}
            )
        )
        self.context_menu_manager.attachment_requested.connect(
            lambda doc: self.document_action_triggered.emit("attachment", doc)
        )
        self.context_menu_manager.reply_attachment_requested.connect(
            lambda doc: self.document_action_triggered.emit("reply_attachment", doc)
        )
        self.context_menu_manager.delete_requested.connect(
            lambda doc: self.document_action_triggered.emit("delete", doc)
        )
        self.context_menu_manager.pin_toggle_requested.connect(
            lambda doc: self.toggle_pin_document(doc.get('id'))
        )

        self.tableWidget.doubleClicked.connect(self.on_double_click)

    # ========== ПУБЛИЧНЫЕ МЕТОДЫ ==========

    def load_documents(self, documents: list, doc_type: str = None, title: str = None, view_mode: str = None):
        """
        Загрузить документы в таблицу.
        """
        try:
            self._is_loading = True

            if not doc_type:
                doc_type = "default"
            if not view_mode:
                view_mode = "all"

            # ПРОВЕРЯЕМ: изменился ли тип документа
            old_doc_type = self._current_doc_type
            self._current_doc_type = str(doc_type)
            self._current_view_mode = view_mode

            # ЕСЛИ ТИП ИЗМЕНИЛСЯ - перестраиваем TableBuilder с новым типом
            if old_doc_type != self._current_doc_type or view_mode != self._current_view_mode:
                # Сохраняем настройки старого типа перед перестроением
                if hasattr(self, 'table_builder') and hasattr(self.table_builder, 'column_manager'):
                    self.table_builder.column_manager.save_all()
                if hasattr(self, 'row_manager'):
                    self.row_manager.save_row_heights()

                # Перестраиваем с новым типом
                self._rebuild_table_builder(self._current_doc_type, self._current_view_mode)
            else:
                # Если тип не изменился, просто обновляем колонки
                # (например, при обновлении данных того же типа)
                pass

            # Добавляем is_pinned
            for doc in documents:
                if 'is_pinned' not in doc:
                    doc['is_pinned'] = False

            # Загружаем данные
            self.data_manager.load_data(documents)

            # Применяем закрепление
            if self.row_manager:
                self.row_manager._apply_pinning()
                self._update_all_pin_icons()

            # Восстанавливаем высоты ПОСЛЕ загрузки данных
            QTimer.singleShot(300, self._restore_heights_after_load)

            self.data_loaded.emit(len(documents))
            print(
                f"[DocumentsTable] Loaded {len(documents)} documents, doc_type: {self._current_doc_type}, view_mode: {self._current_view_mode}")

        except Exception as e:
            print(f"[DocumentsTable] Error loading documents: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._is_loading = False

    def _restore_heights_after_load(self):
        """Восстановление высот после загрузки данных"""
        # Восстанавливаем размеры колонок
        if hasattr(self, 'table_builder') and hasattr(self.table_builder, 'column_manager'):
            self.table_builder.column_manager.restore_column_sizes()

        # Восстанавливаем высоты строк - теперь данные уже загружены
        if hasattr(self, 'row_manager'):
            self.row_manager.restore_row_heights()

    def clear(self):
        """Очистить таблицу"""
        self.tableWidget.setRowCount(0)
        self.tableWidget.setColumnCount(0)

    def set_doc_type(self, doc_type: str):
        """Установить тип документа"""
        if doc_type:
            self._current_doc_type = str(doc_type)
            self._rebuild_table_builder(self._current_doc_type, self._current_view_mode)

    def set_view_mode(self, view_mode: str):
        """Установить режим просмотра"""
        if view_mode in ["all", "type", "direction"]:
            self._current_view_mode = view_mode
            self._rebuild_table_builder(self._current_doc_type, self._current_view_mode)

    # ========== ЗАКРЕПЛЕНИЕ ==========

    def toggle_pin_document(self, document_id: int):
        """Переключение закрепления документа"""
        if self.row_manager:
            self.row_manager.toggle_pin(document_id)
            self._update_document_pin_status(document_id)
            is_pinned = self.row_manager.is_pinned(document_id)
            self.pin_status_changed.emit(document_id, is_pinned)

    def is_document_pinned(self, document_id: int) -> bool:
        return self.row_manager.is_pinned(document_id) if self.row_manager else False

    def _update_document_pin_status(self, document_id: int):
        """Обновление is_pinned в данных и UI"""
        if not self.row_manager:
            return

        is_pinned = self.row_manager.is_pinned(document_id)
        reg_number_col = self._get_reg_number_column()

        for row in range(self.tableWidget.rowCount()):
            item = self.tableWidget.item(row, reg_number_col)
            if item:
                doc_data = item.data(Qt.ItemDataRole.UserRole)
                if doc_data and doc_data.get("id") == document_id:
                    doc_data["is_pinned"] = is_pinned
                    item.setData(Qt.ItemDataRole.UserRole, doc_data)
                    reg_number = doc_data.get("reg_number", "")
                    item.setText(str(reg_number))
                    if is_pinned:
                        pin_icon = icon_manager.get_icon('pin', QSize(16, 16))
                        item.setIcon(pin_icon)
                    else:
                        item.setIcon(QIcon())
                    break

    def _update_all_pin_icons(self):
        """Обновление всех иконок закрепления"""
        if not self.row_manager:
            return

        reg_number_col = self._get_reg_number_column()

        for row in range(self.tableWidget.rowCount()):
            item = self.tableWidget.item(row, reg_number_col)
            if item:
                doc_data = item.data(Qt.ItemDataRole.UserRole)
                if doc_data:
                    doc_id = doc_data.get("id")
                    is_pinned = self.row_manager.is_pinned(doc_id)
                    doc_data["is_pinned"] = is_pinned
                    item.setData(Qt.ItemDataRole.UserRole, doc_data)
                    reg_number = doc_data.get("reg_number", "")
                    item.setText(str(reg_number))
                    if is_pinned:
                        pin_icon = icon_manager.get_icon('pin', QSize(16, 16))
                        item.setIcon(pin_icon)
                    else:
                        item.setIcon(QIcon())

    # ========== КОНТЕКСТНОЕ МЕНЮ ==========

    def show_context_menu(self, position):
        """Отображение контекстного меню"""
        index = self.tableWidget.indexAt(position)
        if not index.isValid():
            return

        row = index.row()

        document_data = self._get_document_from_row(row)
        if not document_data:
            return

        doc_id = document_data.get("id")
        if doc_id:
            document_data["is_pinned"] = self.is_document_pinned(doc_id)

        self.tableWidget.selectRow(row)

        has_reply = document_data.get("has_reply", False)
        menu = self.context_menu_manager.create_menu(document_data, has_reply)

        global_pos = self.tableWidget.viewport().mapToGlobal(position)
        menu.exec(global_pos)

    def on_double_click(self, index):
        """Обработка двойного клика"""
        row = index.row()
        if row < 0:
            return

        document_data = self._get_document_from_row(row)
        if not document_data:
            return

        visual_rect = self.tableWidget.visualRect(index)
        position = QPoint(
            visual_rect.x() + visual_rect.width() // 2,
            visual_rect.y() + visual_rect.height() // 2
        )

        self.show_context_menu(position)

    def get_selected_document(self):
        """Получение выделенного документа"""
        current_row = self.tableWidget.currentRow()
        if current_row < 0:
            return None

        return self._get_document_from_row(current_row)

    def update_document_read_status(self, document_id, is_read):
        """Обновление статуса прочтения"""
        reg_number_col = self._get_reg_number_column()

        for row in range(self.tableWidget.rowCount()):
            item = self.tableWidget.item(row, reg_number_col)
            if item:
                doc_data = item.data(Qt.ItemDataRole.UserRole)
                if doc_data and doc_data.get("id") == document_id:
                    # Находим колонку "Прочитано" в актуальной конфигурации
                    columns_config = self._get_columns_config(self._current_doc_type, self._current_view_mode)
                    col_map = {name: idx for idx, name in columns_config.items()}
                    read_col = col_map.get("Прочитано")
                    if read_col is not None:
                        read_widget = self.tableWidget.cellWidget(row, read_col)
                        if read_widget and hasattr(read_widget, 'set_read_state'):
                            read_widget.set_read_state(is_read)
                    break

    def closeEvent(self, event):
        """Сохранение настроек при закрытии"""
        try:
            # Сохраняем высоты строк
            if hasattr(self, 'row_manager'):
                self.row_manager.save_row_heights()

            # Сохраняем настройки колонок
            if hasattr(self, 'table_builder') and hasattr(self.table_builder, 'column_manager'):
                self.table_builder.column_manager.save_all()

            print(f"[DocumentsTable] Settings saved for doc_type: {self._current_doc_type}")

        except Exception as e:
            print(f"[DocumentsTable] Error saving settings: {e}")

        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DocumentsTable()
    window.setWindowTitle("Documents Table Test")
    window.resize(1600, 600)
    window.show()

    from client.core.data.document_repository import document_repository
    window.load_documents(document_repository.get_all_documents(), "default", "Все документы", "all")

    sys.exit(app.exec())