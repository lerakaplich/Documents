"""
Панель документов - управление данными и UI
"""
import os
import sys
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import pyqtSignal
from PyQt6.uic import loadUi

from client.core.data.document_data import DocumentDataConfig
from client.windows.documents.menus.column_menu import ColumnsMenu
from client.windows.documents.menus.filter_menu import FilterMenu
from client.windows.documents.menus.status_menu import StatusesMenu
from client.windows.documents.table.documents_table import DocumentsTable
from client.core.table.documents_panel_controller import DocumentsPanelController

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

class DocumentsPanel(QWidget):
    """
    Панель документов - контейнер с UI элементами.
    Управляет загрузкой данных и навигацией.
    """

    # Сигналы
    filter_changed = pyqtSignal(dict)
    search_requested = pyqtSignal(str)
    document_selected = pyqtSignal(dict)
    document_action_triggered = pyqtSignal(str, dict)
    pin_status_changed = pyqtSignal(int, bool)

    # Сигналы состояния
    data_loaded = pyqtSignal(int)
    type_changed = pyqtSignal(int)
    direction_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Контроллер логики (вынесен в core)
        self.controller = DocumentsPanelController()

        # Текущее состояние (дублируется для удобства доступа извне,
        # но основное состояние хранится в контроллере)
        self.current_type_id = None
        self.current_direction = None
        self.current_query = ""
        self.current_title = "Все документы"
        self.current_view_mode = "all"

        self._init_ui()
        self._init_table()
        self._connect_signals()

        # Загружаем все документы по умолчанию
        self.load_all_documents()
        self.documents_table.document_action_triggered.connect(self._on_document_action)

    def _init_ui(self):
        """Загрузка UI из .ui файла"""
        ui_path = os.path.join(ROOT_DIR, "client", "ui", "documents", "table", "documents_panel.ui")
        loadUi(ui_path, self)
        self._setup_buttons()

    def _init_table(self):
        """Создание и добавление таблицы"""
        self.documents_table = DocumentsTable()

        if hasattr(self, 'contentFrame'):
            self.contentLayout.addWidget(self.documents_table)
        elif hasattr(self, 'horizontalLayoutHeader'):
            self.verticalLayout.addWidget(self.documents_table)
        elif hasattr(self, 'panelLayout'):
            self.panelLayout.addWidget(self.documents_table)
        else:
            self.layout().addWidget(self.documents_table)

    def _setup_buttons(self):
        """Настройка кнопок и их меню (с использованием новых классов меню)"""
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
        """Подключение сигналов"""
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

    # ========== ЗАГРУЗКА ДАННЫХ ==========

    def load_all_documents(self):
        """Загрузить все документы"""
        documents, title, view_mode, doc_type = self.controller.load_all_documents()
        self._sync_state_from_controller()
        self._update_table(documents, doc_type, title, view_mode)
        self.data_loaded.emit(len(documents))

    def load_documents_by_type(self, type_id: int):
        """Загрузить документы по типу - оптимизированно"""
        documents, title, view_mode, doc_type = self.controller.load_documents_by_type(type_id)
        self._sync_state_from_controller()
        self._update_table(documents, doc_type, title, view_mode)
        self.type_changed.emit(type_id)
        self.data_loaded.emit(len(documents))

    def load_documents_by_direction(self, direction: str, title: str = None):
        """Загрузить документы по направлению"""
        documents, title, view_mode, doc_type = self.controller.load_documents_by_direction(direction, title)
        self._sync_state_from_controller()
        self._update_table(documents, doc_type, title, view_mode)
        self.direction_changed.emit(direction)
        self.data_loaded.emit(len(documents))

    def _update_table(self, documents: list, doc_type: str = None, title: str = None, view_mode: str = None):
        """Обновить таблицу"""
        try:
            doc_type = doc_type or "default"
            view_mode = view_mode or self.current_view_mode or "all"

            self.documents_table._controller.switch_doc_type(doc_type, documents, view_mode)

            if title and hasattr(self, 'labelTitle'):
                self.labelTitle.setText(title)

        except Exception as e:
            print(f"[DocumentsPanel] Error updating table: {e}")
            import traceback
            traceback.print_exc()

    def _sync_state_from_controller(self):
        """Синхронизация локального состояния с контроллером (для обратной совместимости)"""
        self.current_type_id = self.controller.current_type_id
        self.current_direction = self.controller.current_direction
        self.current_query = self.controller.current_query
        self.current_title = self.controller.current_title
        self.current_view_mode = self.controller.current_view_mode

    # ========== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ==========

    def on_search_changed(self, text):
        """Обработка поиска"""
        self.current_query = text
        self.search_requested.emit(text)
        documents, title, view_mode, doc_type = self.controller.search_documents(text)
        self._update_table(documents, doc_type, title, view_mode)
        self.current_title = title
        self.current_view_mode = view_mode

    def update_title(self, title):
        """Обновление заголовка"""
        if hasattr(self, 'labelTitle'):
            self.labelTitle.setText(title)
        self.current_title = title
        self.controller.current_title = title

    def get_documents_table(self):
        """Получение объекта таблицы"""
        return self.documents_table

    def refresh(self):
        """Обновить текущие данные"""
        documents, title, view_mode, doc_type = self.controller.refresh()
        self._sync_state_from_controller()
        self._update_table(documents, doc_type, title, view_mode)

    # ========== ОБРАБОТЧИКИ ДЕЙСТВИЙ ==========

    def _on_document_action(self, action_type: str, document_data: dict):
        """Обработка действий из таблицы"""
        if action_type == "redirect":
            self._handle_redirect(document_data)
        elif action_type == "comment":
            self._handle_comment(document_data)

    def _handle_redirect(self, document_data: dict):
        """Открытие диалога перенаправления"""
        try:
            from client.windows.documents.redirect.redirect_dialog import RedirectDialog

            current_recipients = document_data.get("delegates", [])
            doc_id = document_data.get("id")

            all_employees = [
                {"id": 1, "name": "Иванов И.И."},
                {"id": 2, "name": "Петров П.П."},
                {"id": 3, "name": "Морозов М.М."},
                {"id": 4, "name": "Сидоров С.С."}
            ]

            dialog = RedirectDialog(current_recipients, all_employees, parent=self)
            dialog.redirect_confirmed.connect(
                lambda ids, comment: self._confirm_redirect(doc_id, ids, comment)
            )

            dialog.exec()

        except Exception as e:
            import traceback
            traceback.print_exc()

    def _confirm_redirect(self, document_id: int, recipient_ids: list, comment: str):
        """Подтверждение перенаправления"""
        success = self.controller.redirect_document(document_id, recipient_ids, comment)
        if success:
            self.refresh()

    def _handle_comment(self, document_data: dict):
        """Открытие диалога комментариев"""
        try:
            from client.windows.documents.comments.comment_dialog import CommentDialog
            from client.core.data.document_data import DocumentDataConfig

            doc_id = document_data.get("id")

            # Получаем документ из данных
            full_doc = DocumentDataConfig.get_document_by_id(doc_id)

            if full_doc:
                document_to_pass = full_doc.copy()
                print(f"[DocumentsPanel] Loaded document {doc_id} with {len(document_to_pass.get('comments', []))} comments")
            else:
                document_to_pass = document_data.copy()
                print(f"[DocumentsPanel] Using partial document data for {doc_id}")

            # Нормализация ключей
            if "reg_number" in document_to_pass and "number" not in document_to_pass:
                document_to_pass["number"] = document_to_pass.get("reg_number", "")
            if "title" in document_to_pass and "subject" not in document_to_pass:
                document_to_pass["subject"] = document_to_pass.get("title", "")

            current_user = self._get_current_user()

            dialog = CommentDialog(
                document_data=document_to_pass,
                parent=self,
                current_user=current_user
            )

            dialog.comment_added.connect(
                lambda comment: self._on_comment_added(doc_id, comment)
            )

            dialog.exec()

        except Exception as e:
            import traceback
            print(f"[DocumentsPanel] Error opening comment dialog: {e}")
            traceback.print_exc()

    def _on_comment_added(self, document_id: int, new_comment: dict):
        """Обработка добавления комментария"""
        try:
            from client.core.data.document_data import DocumentDataConfig

            doc = DocumentDataConfig.get_document_by_id(document_id)
            if doc:
                if 'comments' not in doc:
                    doc['comments'] = []
                doc['comments'].append(new_comment)
                doc['last_comment_text'] = new_comment.get('text', '')

            self.refresh()
            print(f"[DocumentsPanel] Комментарий добавлен к документу {document_id}")

        except Exception as e:
            print(f"[DocumentsPanel] Error saving comment: {e}")

    def _get_current_user(self) -> dict:
        """Возвращает текущего пользователя (для разработки)"""
        return {
            'id': 2,
            'full_name': 'Сидоров С.С.',
            'last_name': 'Сидоров',
            'first_name': 'Сергей',
            'middle_name': 'Сергеевич'
        }


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DocumentsPanel()
    window.setWindowTitle("Documents Panel Test")
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec())