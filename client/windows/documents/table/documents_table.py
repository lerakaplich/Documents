"""
Основной модуль таблицы документов
"""
import sys
from PyQt6.QtWidgets import (QWidget, QTableWidget, QApplication,
                             QVBoxLayout, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint

from client.windows.documents.table.document_data import DocumentDataConfig
from client.windows.documents.table.styles import TableStyles
from client.windows.documents.table.table_setup import TableSetup
from client.windows.documents.table.row_filler import RowFiller
from client.windows.documents.table.context_menu import ContextMenu


class DocumentsTable(QWidget):
    """Таблица документов с поддержкой хэштегов, чекбоксов и контекстного меню"""

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
        self.table_setup = TableSetup(self.tableWidget, self.config.COLUMNS_CONFIG)
        self.table_setup.setup()

        self.row_filler = RowFiller(self.tableWidget, self.config, self)
        self.context_menu_manager = ContextMenu(self)

    def _connect_signals(self):
        """Подключение сигналов"""
        # Контекстное меню
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

        # Двойной клик
        self.tableWidget.doubleClicked.connect(self.on_double_click)

    # ==================== Публичные методы ====================
    def force_refresh(self):
        """Принудительное обновление таблицы"""
        self.tableWidget.viewport().update()
        self.tableWidget.update()
        self.tableWidget.repaint()

    def get_row_manager(self):
        return self.table_setup.get_row_manager()

    def load_test_data(self):
        """Загрузка тестовых данных"""
        # Добавляем is_pinned в тестовые данные
        for doc in self.config.TEST_DATA:
            if 'is_pinned' not in doc:
                doc['is_pinned'] = False

        # Загружаем данные
        self.populate_table(self.config.TEST_DATA)

        # ПОСЛЕ загрузки применяем закрепление
        self._apply_pinning_after_load()

    def populate_table(self, documents):
        """Заполнение таблицы данными"""
        self.tableWidget.setRowCount(0)
        self.tableWidget.setRowCount(len(documents))

        for row, doc in enumerate(documents):
            # Не перезаписываем is_pinned, если он уже есть
            if 'is_pinned' not in doc:
                doc['is_pinned'] = False
            self.row_filler.fill_row(row, doc)

        self.tableWidget.resizeRowsToContents()

    # ==================== Закрепление ====================

    def toggle_pin_document(self, document_id: int):
        """Переключение закрепления документа"""
        print(f"[DocumentsTable] toggle_pin_document: {document_id}")
        row_manager = self.get_row_manager()
        if row_manager:
            row_manager.toggle_pin(document_id)
            self._update_document_pin_status(document_id)
            is_pinned = row_manager.is_pinned(document_id)
            self.pin_status_changed.emit(document_id, is_pinned)

            # ПРИНУДИТЕЛЬНОЕ ОБНОВЛЕНИЕ
            self.tableWidget.viewport().update()
            self.tableWidget.update()
            self.tableWidget.repaint()
            QApplication.processEvents()

    def is_document_pinned(self, document_id: int) -> bool:
        row_manager = self.get_row_manager()
        return row_manager.is_pinned(document_id) if row_manager else False

    def _update_document_pin_status(self, document_id: int):
        """Обновление is_pinned в данных и UI"""
        row_manager = self.get_row_manager()
        if not row_manager:
            return

        is_pinned = row_manager.is_pinned(document_id)

        for row in range(self.tableWidget.rowCount()):
            item = self.tableWidget.item(row, 0)
            if item:
                doc_data = item.data(Qt.ItemDataRole.UserRole)
                if doc_data and doc_data.get("id") == document_id:
                    doc_data["is_pinned"] = is_pinned
                    item.setData(Qt.ItemDataRole.UserRole, doc_data)
                    doc_id_str = str(document_id)
                    display_text = f"📌 {doc_id_str}" if is_pinned else doc_id_str
                    item.setText(display_text)
                    break

    def _apply_pinning_after_load(self):
        """Применение закрепления после загрузки"""
        row_manager = self.get_row_manager()
        if row_manager:
            print("[DocumentsTable] === APPLYING PINNING AFTER LOAD ===")
            print(f"[DocumentsTable] Pinned IDs: {row_manager.pinned_ids}")
            row_manager.apply_initial_pinning()
            self._update_all_pin_icons()
            print("[DocumentsTable] Pinning applied successfully")

    def _update_all_pin_icons(self):
        """Обновление всех иконок закрепления"""
        row_manager = self.get_row_manager()
        if not row_manager:
            return

        for row in range(self.tableWidget.rowCount()):
            item = self.tableWidget.item(row, 0)
            if item:
                doc_data = item.data(Qt.ItemDataRole.UserRole)
                if doc_data:
                    doc_id = doc_data.get("id")
                    is_pinned = row_manager.is_pinned(doc_id)
                    doc_data["is_pinned"] = is_pinned
                    item.setData(Qt.ItemDataRole.UserRole, doc_data)
                    doc_id_str = str(doc_id)
                    display_text = f"📌 {doc_id_str}" if is_pinned else doc_id_str
                    item.setText(display_text)

    # ==================== Контекстное меню ====================

    def show_context_menu(self, position):
        """Отображение контекстного меню"""
        index = self.tableWidget.indexAt(position)
        if not index.isValid():
            return

        row = index.row()
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

    # ==================== Вспомогательные методы ====================

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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DocumentsTable()
    window.setWindowTitle("Documents Table Test")
    window.resize(1600, 600)
    window.show()
    sys.exit(app.exec())