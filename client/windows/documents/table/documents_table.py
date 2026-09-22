"""
Основной модуль таблицы документов - ТОЛЬКО UI
"""
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QWidget, QTableWidget, QApplication, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QSize

from client.core.data.document_data import DocumentDataConfig
from client.core.table.managers.table_data_manager import TableDataManager
from client.core.table.table_builder import TableBuilder
from client.core.table.table_updater import TableUpdater
from client.core.utils.icon_manager import icon_manager
from client.windows.documents.table.builders.row_renderer import RowRenderer
from client.windows.documents.table.styles import TableStyles
from client.windows.documents.table.context_menu import ContextMenu
from client.core.table.table_controller import TableController


class DocumentsTable(QWidget):
    """
    Таблица документов - ТОЛЬКО UI компонент.
    Все, что связано с бизнес-логикой, вынесено в TableController.
    """

    # Сигналы для внешнего мира
    document_action_triggered = pyqtSignal(str, dict)
    read_status_changed = pyqtSignal(int, bool)
    attachment_added = pyqtSignal(int, str)
    attachment_opened = pyqtSignal(int, str)
    reply_attachment_added = pyqtSignal(int, str)
    pin_status_changed = pyqtSignal(int, bool)
    data_loaded = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._init_ui()
        self._init_components()
        self._connect_signals()

    def _init_ui(self):
        """Только UI - внешний вид и расположение элементов"""
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
        """Инициализация компонентов - создание, но без логики"""
        self.config = DocumentDataConfig()
        self.row_renderer = RowRenderer(self.tableWidget, self.config, self)
        self.data_manager = TableDataManager(self.tableWidget, self.row_renderer)
        self.updater = TableUpdater(self.tableWidget)

        # Создаем контроллер - вся логика здесь
        self._controller = TableController(
            table_widget=self.tableWidget,
            data_manager=self.data_manager,
            row_renderer=self.row_renderer,
            updater=self.updater
        )

        self.context_menu_manager = ContextMenu(self)

    def _connect_signals(self):
        """Подключение сигналов - только UI события"""
        self.tableWidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tableWidget.customContextMenuRequested.connect(self._on_context_menu)

        # Проксируем сигналы контекстного меню
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
            lambda doc: self._controller.toggle_pin(doc.get('id'))
        )

        self.tableWidget.doubleClicked.connect(self._on_double_click)

        # Подписываемся на сигналы контроллера
        self._controller.pin_status_changed.connect(self.pin_status_changed.emit)
        self._controller.data_loaded.connect(self.data_loaded.emit)

    # ========== ПУБЛИЧНЫЕ МЕТОДЫ - только делегирование ==========

    def load_documents(self, documents: list, doc_type: str = None, title: str = None, view_mode: str = None):
        """Загрузить документы - делегируем контроллеру"""
        self._controller.load_documents(documents, doc_type, view_mode)

    def clear(self):
        """Очистить таблицу"""
        self.tableWidget.setRowCount(0)
        self.tableWidget.setColumnCount(0)

    def reapply_theme(self):
        """Переприменить стили таблицы к актуальной теме."""
        self.setStyleSheet(TableStyles.get_main_style())
        self.tableWidget.setStyleSheet(TableStyles.get_table_style())

    def get_selected_document(self):
        """Получение выделенного документа"""
        return self._controller.get_selected_document()

    def update_document_read_status(self, document_id, is_read):
        """Обновление статуса прочтения - делегируем контроллеру"""
        self._controller.update_read_status(document_id, is_read)

    # ========== PRIVATE UI МЕТОДЫ ==========

    def _on_context_menu(self, position):
        """Показать контекстное меню - только UI"""
        index = self.tableWidget.indexAt(position)
        if not index.isValid():
            return

        row = index.row()
        document_data = self._controller.get_document_at_row(row)
        if not document_data:
            return

        doc_id = document_data.get("id")
        if doc_id:
            document_data["is_pinned"] = self._controller.is_pinned(doc_id)

        self.tableWidget.selectRow(row)

        has_reply = document_data.get("has_reply", False)
        menu = self.context_menu_manager.create_menu(document_data, has_reply)

        global_pos = self.tableWidget.viewport().mapToGlobal(position)
        menu.exec(global_pos)

    def _on_double_click(self, index):
        """Обработка двойного клика - только UI"""
        row = index.row()
        if row < 0:
            return

        document_data = self._controller.get_document_at_row(row)
        if not document_data:
            return

        visual_rect = self.tableWidget.visualRect(index)
        position = QPoint(
            visual_rect.x() + visual_rect.width() // 2,
            visual_rect.y() + visual_rect.height() // 2
        )

        self._on_context_menu(position)

    def closeEvent(self, event):
        """Сохранение настроек при закрытии - делегируем контроллеру"""
        self._controller.save_state()
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