"""
Панель документов - управление данными и UI
"""
import os
import sys
from PyQt6.QtWidgets import QWidget, QApplication, QVBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.uic import loadUi

from client.core.data.document_data import DocumentDataConfig
from client.windows.documents.menus.column_menu import ColumnsMenu
from client.windows.documents.menus.filter_menu import FilterMenu
from client.windows.documents.menus.status_menu import StatusesMenu
from client.windows.documents.table.documents_table import DocumentsTable
from client.core.table.documents_panel_controller import DocumentsPanelController

# Импортируем вашу плавающую кнопку
from client.windows.animations.floating_action_button import FloatingActionButton

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


# client/windows/documents/table/documents_panel.py

# ... (все ваши импорты остаются прежними)

class DocumentsPanel(QWidget):
    """
    Панель документов - контейнер с UI элементами.
    Отвечает исключительно за отображение данных и реакцию на действия пользователя.
    """

    # Сигналы
    filter_changed = pyqtSignal(dict)
    search_requested = pyqtSignal(str)
    document_selected = pyqtSignal(dict)
    document_action_triggered = pyqtSignal(str, dict)
    pin_status_changed = pyqtSignal(int, bool)

    data_loaded = pyqtSignal(int)
    type_changed = pyqtSignal(int)
    direction_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Контроллер бизнес-логики
        self.controller = DocumentsPanelController()

        # СОСТОЯНИЕ УДАЛЕНО! (Все данные лежат в self.controller)

        self._init_ui()
        self._init_table()
        self._connect_signals()
        self._init_floating_button()

        # Загружаем все документы по умолчанию
        self.load_all_documents()
        self.documents_table.document_action_triggered.connect(self._on_document_action)

    # ========== UI И КНОПКИ (Оставляем как есть) ==========
    def _init_ui(self):
        ui_path = os.path.join(ROOT_DIR, "client", "ui", "documents", "table", "documents_panel.ui")
        loadUi(ui_path, self)
        self._setup_buttons()

    def _init_table(self):
        self.documents_table = DocumentsTable()
        if hasattr(self, 'contentFrame'):
            self.contentLayout.addWidget(self.documents_table)
        elif hasattr(self, 'horizontalLayoutHeader'):
            self.verticalLayout.addWidget(self.documents_table)
        elif hasattr(self, 'panelLayout'):
            self.panelLayout.addWidget(self.documents_table)
        else:
            self.layout().addWidget(self.documents_table)

    def _init_floating_button(self):
        self.floating_btn = FloatingActionButton(self)
        self.floating_btn.clicked.connect(self.on_add_document_clicked)
        if hasattr(self.documents_table, 'tableWidget'):
            scrollbar = self.documents_table.tableWidget.verticalScrollBar()
            scrollbar.valueChanged.connect(self.on_scroll)
        self.position_floating_button()

    def _setup_buttons(self):
        if hasattr(self, 'columnsBtn'):
            self.columns_menu = ColumnsMenu(parent=self)
            self.columnsBtn.setMenu(self.columns_menu)

        if hasattr(self, 'filterBtn'):
            self.filter_menu = FilterMenu(self)
            self.filterBtn.setMenu(self.filter_menu)

        if hasattr(self, 'statusesBtn'):
            self.statuses_menu = StatusesMenu(self)
            self.statusesBtn.setMenu(self.statuses_menu)
            self.statuses_menu.connect_clear_signal(self.statuses_menu.clear_selection)

        if hasattr(self, 'searchEdit'):
            self.searchEdit.textChanged.connect(self.on_search_changed)

    def _connect_signals(self):
        if hasattr(self, 'documents_table'):
            self.documents_table.document_action_triggered.connect(
                self.document_action_triggered.emit
            )
            self.documents_table.read_status_changed.connect(
                lambda doc_id, is_read: print(f"Document {doc_id} read: {is_read}")
            )
            self.documents_table.pin_status_changed.connect(
                self.pin_status_changed.emit
            )
            self.documents_table.data_loaded.connect(
                self.data_loaded.emit
            )

    # ========== ЛОГИКА ПЛАВАЮЩЕЙ КНОПКИ (Оставляем во View) ==========
    def position_floating_button(self):
        if hasattr(self, 'floating_btn'):
            margin = 30
            x = self.width() - self.floating_btn.width() - margin
            y = self.height() - self.floating_btn.height() - margin
            self.floating_btn.update_base_position(x, y)
            self.floating_btn.raise_()

    def on_scroll(self, value):
        if hasattr(self, 'floating_btn'):
            self.floating_btn.hide_with_animation()
            self.floating_btn.start_hide_timer()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.position_floating_button()

    def on_add_document_clicked(self):
        print("Нажата кнопка добавления нового документа!")

    # ========== ЗАГРУЗКА И ОТОБРАЖЕНИЕ ДАННЫХ ==========

    def load_all_documents(self):
        """Запросить данные у контроллера и отобразить их"""
        documents, title, view_mode, doc_type = self.controller.load_all_documents()
        self._update_table(documents, doc_type, title, view_mode)
        self.data_loaded.emit(len(documents))

    def load_documents_by_type(self, type_id: int):
        documents, title, view_mode, doc_type = self.controller.load_documents_by_type(type_id)
        self._update_table(documents, doc_type, title, view_mode)
        self.type_changed.emit(type_id)
        self.data_loaded.emit(len(documents))

    def load_documents_by_direction(self, direction: str, title: str = None):
        documents, title, view_mode, doc_type = self.controller.load_documents_by_direction(direction, title)
        self._update_table(documents, doc_type, title, view_mode)
        self.direction_changed.emit(direction)
        self.data_loaded.emit(len(documents))

    def _update_table(self, documents: list, doc_type: str = None, title: str = None, view_mode: str = None):
        """Обновить UI-компонент таблицы"""
        try:
            doc_type = doc_type or "default"
            # Читаем режим напрямую из контроллера
            view_mode = view_mode or self.controller.current_view_mode or "all"

            self.documents_table._controller.switch_doc_type(doc_type, documents, view_mode)

            if title and hasattr(self, 'labelTitle'):
                self.labelTitle.setText(title)

        except Exception as e:
            print(f"[DocumentsPanel] Error updating table: {e}")
            import traceback
            traceback.print_exc()

    def refresh(self):
        """Перезагрузить текущие данные через контроллер"""
        documents, title, view_mode, doc_type = self.controller.refresh()
        self._update_table(documents, doc_type, title, view_mode)

    # ========== ОБРАБОТЧИКИ СОБЫТИЙ С СЕНДВЕЕМ К КОНТРОЛЛЕРУ ==========

    def on_search_changed(self, text):
        self.search_requested.emit(text)
        documents, title, view_mode, doc_type = self.controller.search_documents(text)
        self._update_table(documents, doc_type, title, view_mode)

    def update_title(self, title):
        if hasattr(self, 'labelTitle'):
            self.labelTitle.setText(title)
        self.controller.current_title = title

    def get_documents_table(self):
        return self.documents_table

    def _on_document_action(self, action_type: str, document_data: dict):
        if action_type == "redirect":
            self._handle_redirect_document(document_data)
        elif action_type == "comment":
            self._handle_comment_document(document_data)

    def _handle_redirect_document(self, document_data: dict):
        """Отображение диалога перенаправления"""
        try:
            from client.windows.documents.redirect.redirect_dialog import RedirectDialog

            doc_id = document_data.get("id")
            current_recipients = document_data.get("delegates", [])

            # Контроллер отдает список сотрудников
            all_employees = self.controller.get_employees_for_redirect()

            dialog = RedirectDialog(current_recipients, all_employees, parent=self)
            dialog.redirect_confirmed.connect(
                lambda ids, comment: self._confirm_redirect(doc_id, ids, comment)
            )
            dialog.exec()
        except Exception as e:
            import traceback
            traceback.print_exc()

    def _confirm_redirect(self, document_id: int, recipient_ids: list, comment: str):
        # Делегируем логику сохранения контроллеру
        success = self.controller.redirect_document(document_id, recipient_ids, comment)
        if success:
            self.refresh()

    def _handle_comment_document(self, document_data: dict):
        """Отображение диалога комментариев"""
        try:
            from client.windows.documents.comments.comment_dialog import CommentDialog

            # Контроллер готовит полный объект документа
            document_to_pass = self.controller.get_full_document_for_comment(document_data)
            current_user = self.controller.get_current_user()

            dialog = CommentDialog(
                document_data=document_to_pass,
                parent=self,
                current_user=current_user
            )
            dialog.comment_added.connect(
                lambda comment: self._on_comment_added(document_data.get("id"), comment)
            )
            dialog.exec()
        except Exception as e:
            import traceback
            print(f"[DocumentsPanel] Error opening comment dialog: {e}")
            traceback.print_exc()

    def _on_comment_added(self, document_id: int, new_comment: dict):
        # Делегируем логику сохранения контроллеру
        success = self.controller.add_comment_to_document(document_id, new_comment)
        if success:
            self.refresh()
            print(f"[DocumentsPanel] Комментарий сохранен через контроллер для документа {document_id}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DocumentsPanel()
    window.setWindowTitle("Documents Panel Test")
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec())