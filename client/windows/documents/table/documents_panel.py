"""
Панель документов - управление данными и UI
"""
import os
import sys
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import pyqtSignal
from PyQt6.uic import loadUi

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
            # Исправлено: передаём parent по ключевому слову
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

            # Используем switch_doc_type для более эффективного переключения
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
        # Синхронизируем состояние после поиска
        self.current_title = title
        self.current_view_mode = view_mode

    def update_title(self, title):
        """Обновление заголовка"""
        if hasattr(self, 'labelTitle'):
            self.labelTitle.setText(title)
        self.current_title = title
        self.controller.current_title = title   # поддерживаем синхронизацию

    def get_documents_table(self):
        """Получение объекта таблицы"""
        return self.documents_table

    def refresh(self):
        """Обновить текущие данные"""
        documents, title, view_mode, doc_type = self.controller.refresh()
        self._sync_state_from_controller()
        self._update_table(documents, doc_type, title, view_mode)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DocumentsPanel()
    window.setWindowTitle("Documents Panel Test")
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec())