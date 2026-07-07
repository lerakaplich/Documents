"""
Основной модуль таблицы документов
"""
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (QWidget, QTableWidget, QApplication,
                             QVBoxLayout)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize

from client.core.settings.settings_keys import SettingsKeys
from client.core.settings.settings_manager import SettingsManager
from client.core.table.table_builder import TableBuilder
from client.core.table.table_data_manager import TableDataManager
from client.core.table.table_updater import TableUpdater
from client.core.utils.icon_manager import icon_manager
from client.windows.documents.table.builders.row_filler import RowFiller
from client.windows.documents.table.document_data import DocumentDataConfig
from client.windows.documents.table.styles import TableStyles
from client.windows.documents.table.context_menu import ContextMenu


class DocumentsTable(QWidget):
    """Таблица документов"""

    document_action_triggered = pyqtSignal(str, dict)
    read_status_changed = pyqtSignal(int, bool)
    attachment_added = pyqtSignal(int, str)
    attachment_opened = pyqtSignal(int, str)
    reply_attachment_added = pyqtSignal(int, str)
    pin_status_changed = pyqtSignal(int, bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.config = DocumentDataConfig()
        self._init_ui()
        self._init_components()
        self._connect_signals()
        self.load_test_data()

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
        self.row_filler = RowFiller(self.tableWidget, self.config, self)
        self.data_manager = TableDataManager(self.tableWidget, self.row_filler)
        self.updater = TableUpdater(self.tableWidget)

        # Создаем TableBuilder с зависимостями
        self.table_builder = TableBuilder(self.tableWidget, self.config.COLUMNS_CONFIG)
        self.table_builder.setup(self.data_manager, self.updater)

        # Получаем RowManager
        self.row_manager = self.table_builder.get_row_manager()

        # Передаем RowManager в updater для восстановления высот
        self.updater.set_row_manager(self.row_manager)

        self.context_menu_manager = ContextMenu(self)

    def _connect_signals(self):
        """Подключение сигналов"""
        self.tableWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tableWidget.customContextMenuRequested.connect(self.show_context_menu)

        # Сигналы контекстного меню
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

    def load_test_data(self):
        """Загрузка тестовых данных"""
        # Добавляем is_pinned в тестовые данные
        for doc in self.config.TEST_DATA:
            if 'is_pinned' not in doc:
                doc['is_pinned'] = False

        # Загружаем данные
        self.data_manager.load_data(self.config.TEST_DATA)

        # Применяем закрепление
        if self.row_manager:
            self.row_manager._apply_pinning()
            self._update_all_pin_icons()

        # Восстанавливаем размеры и высоты ПОСЛЕ загрузки данных
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(200, self._restore_sizes_after_load)

    def _restore_sizes_after_load(self):
        """Восстановление размеров после загрузки данных"""
        print("[DocumentsTable] Restoring sizes after data load...")

        if hasattr(self, 'table_builder') and hasattr(self.table_builder, 'column_manager'):
            self.table_builder.column_manager.restore_column_sizes()

        if hasattr(self, 'row_manager'):
            self.row_manager.restore_row_heights()

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

        # Получаем индекс колонки "Номер документа"
        col_map = {name: idx for idx, name in enumerate(self.config.COLUMNS_CONFIG.values())}
        reg_number_col = col_map.get("Номер документа", 2)  # обычно это индекс 2

        for row in range(self.tableWidget.rowCount()):
            # Обновляем в колонке "Номер документа"
            item = self.tableWidget.item(row, reg_number_col)
            if item:
                doc_data = item.data(Qt.ItemDataRole.UserRole)
                if doc_data and doc_data.get("id") == document_id:
                    doc_data["is_pinned"] = is_pinned
                    item.setData(Qt.ItemDataRole.UserRole, doc_data)

                    # Обновляем текст (регистрационный номер)
                    reg_number = doc_data.get("reg_number", "")
                    item.setText(str(reg_number))

                    # Обновляем иконку
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

        # Получаем индекс колонки "Номер документа"
        col_map = {name: idx for idx, name in enumerate(self.config.COLUMNS_CONFIG.values())}
        reg_number_col = col_map.get("Номер документа", 2)

        for row in range(self.tableWidget.rowCount()):
            # Обновляем в колонке "Номер документа"
            item = self.tableWidget.item(row, reg_number_col)
            if item:
                doc_data = item.data(Qt.ItemDataRole.UserRole)
                if doc_data:
                    doc_id = doc_data.get("id")
                    is_pinned = self.row_manager.is_pinned(doc_id)
                    doc_data["is_pinned"] = is_pinned
                    item.setData(Qt.ItemDataRole.UserRole, doc_data)

                    # Обновляем текст (регистрационный номер)
                    reg_number = doc_data.get("reg_number", "")
                    item.setText(str(reg_number))

                    # Обновляем иконку
                    if is_pinned:
                        pin_icon = icon_manager.get_icon('pin', QSize(16, 16))
                        item.setIcon(pin_icon)
                    else:
                        item.setIcon(QIcon())

    def show_context_menu(self, position):
        """Отображение контекстного меню"""
        index = self.tableWidget.indexAt(position)
        if not index.isValid():
            return

        row = index.row()
        # Получаем данные из колонки ID (индекс 0)
        item = self.tableWidget.item(row, 0)
        if not item:
            return

        document_data = item.data(Qt.ItemDataRole.UserRole)
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

        item = self.tableWidget.item(row, 0)
        if not item:
            return

        document_data = item.data(Qt.ItemDataRole.UserRole)
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

        item = self.tableWidget.item(current_row, 0)
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def update_document_read_status(self, document_id, is_read):
        """Обновление статуса прочтения"""
        for row in range(self.tableWidget.rowCount()):
            item = self.tableWidget.item(row, 0)
            if item:
                doc_data = item.data(Qt.ItemDataRole.UserRole)
                if doc_data and doc_data.get("id") == document_id:
                    col_map = {name: idx for idx, name in enumerate(self.config.COLUMNS_CONFIG.values())}
                    read_widget = self.tableWidget.cellWidget(row, col_map["Прочитано"])
                    if read_widget and hasattr(read_widget, 'set_read_state'):
                        read_widget.set_read_state(is_read)
                    break

    def closeEvent(self, event):
        """Сохранение настроек при закрытии"""
        try:
            print("[DocumentsTable] Saving settings on close...")

            if hasattr(self, 'row_manager'):
                self.row_manager.save_row_heights()

            if hasattr(self, 'table_builder') and hasattr(self.table_builder, 'column_manager'):
                self.table_builder.column_manager.save_all()

            print("[DocumentsTable] Settings saved successfully")
        except Exception as e:
            print(f"[DocumentsTable] Error saving settings: {e}")

        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DocumentsTable()
    window.setWindowTitle("Documents Table Test")
    window.resize(1600, 600)
    window.show()
    sys.exit(app.exec())