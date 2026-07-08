
"""
Панель документов - управление данными и UI
"""
import os
import sys
from PyQt6.QtWidgets import QWidget, QMenu, QApplication
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.uic import loadUi

from client.windows.documents.table.documents_table import DocumentsTable
from client.windows.documents.table.styles import TableStyles
from client.core.data.document_repository import document_repository
from client.core.data.document_data import DocumentDataConfig

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

        self.repository = document_repository

        # Текущее состояние
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
        """Настройка кнопок и их меню"""
        menu_style = TableStyles.get_menu_style()

        if hasattr(self, 'columnsBtn'):
            self.columnsBtn.setMenu(self._create_columns_menu(menu_style))
        if hasattr(self, 'filterBtn'):
            self.filterBtn.setMenu(self._create_filter_menu(menu_style))
        if hasattr(self, 'statusesBtn'):
            self.statusesBtn.setMenu(self._create_statuses_menu(menu_style))
        if hasattr(self, 'searchEdit'):
            self.searchEdit.textChanged.connect(self.on_search_changed)

    def _create_columns_menu(self, menu_style):
        """Меню выбора столбцов"""
        menu = QMenu(self)
        menu.setStyleSheet(menu_style)

        columns = ["ID", "Номер документа", "Тема", "Тип", "Дата", "Статус", "Отправитель", "Хэштеги"]
        for col in columns:
            action = QAction(col, menu)
            action.setCheckable(True)
            action.setChecked(True)
            menu.addAction(action)

        return menu

    def _create_filter_menu(self, menu_style):
        """Меню фильтрации"""
        menu = QMenu(self)
        menu.setStyleSheet(menu_style)

        unread_action = QAction("Непрочитанные", menu)
        unread_action.setCheckable(True)
        menu.addAction(unread_action)

        read_action = QAction("Прочитанные", menu)
        read_action.setCheckable(True)
        menu.addAction(read_action)

        menu.addSeparator()

        my_docs_action = QAction("Мои документы", menu)
        my_docs_action.setCheckable(True)
        menu.addAction(my_docs_action)

        all_docs_action = QAction("Все документы", menu)
        all_docs_action.setCheckable(True)
        all_docs_action.setChecked(True)
        menu.addAction(all_docs_action)

        menu.addSeparator()

        by_date_action = QAction("По дате (сначала новые)", menu)
        by_date_action.setCheckable(True)
        menu.addAction(by_date_action)

        return menu

    def _create_statuses_menu(self, menu_style):
        """Меню статусов"""
        menu = QMenu(self)
        menu.setStyleSheet(menu_style)

        statuses = ["Черновик", "На рассмотрении", "На подписи", "Подписан", "Завершен"]
        for status in statuses:
            action = QAction(status, menu)
            action.setCheckable(True)
            menu.addAction(action)

        menu.addSeparator()
        clear_action = QAction("Сбросить фильтр статусов", menu)
        menu.addAction(clear_action)

        return menu

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
        documents = self.repository.get_all_documents()
        self.current_type_id = None
        self.current_direction = None
        self.current_title = "Все документы"
        self.current_view_mode = "all"

        self._update_table(documents, "default", "Все документы", "all")
        self.data_loaded.emit(len(documents))

    # documents_panel.py - исправленный метод

    def load_documents_by_type(self, type_id: int):
        """Загрузить документы по типу - оптимизированно"""
        documents = self.repository.get_documents_by_type(type_id)
        self.current_type_id = type_id
        self.current_direction = None
        self.current_view_mode = "type"

        type_info = self.repository.get_document_type_by_id(type_id)
        title = type_info.get('name', f"Тип {type_id}") if type_info else f"Тип {type_id}"
        self.current_title = title

        # Используем оптимизированную загрузку
        self._update_table(documents, str(type_id), title, "type")
        self.type_changed.emit(type_id)
        self.data_loaded.emit(len(documents))

    def load_documents_by_direction(self, direction: str, title: str = None):
        """Загрузить документы по направлению"""
        documents = self.repository.get_documents_by_direction(direction)
        self.current_direction = direction
        self.current_type_id = None
        self.current_view_mode = "direction"

        if title is None:
            title = DocumentDataConfig.DIRECTION_MAPPING.get(direction, direction)
        self.current_title = title

        doc_type = direction if direction in ["incoming", "outgoing", "internal"] else "default"
        self._update_table(documents, doc_type, title, "direction")
        self.direction_changed.emit(direction)
        self.data_loaded.emit(len(documents))

    # В documents_panel.py обновить методы загрузки

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

    # ========== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ==========

    def on_search_changed(self, text):
        """Обработка поиска"""
        self.current_query = text
        self.search_requested.emit(text)

        if text and len(text) >= 3:
            results = self.repository.search_documents(text)
            self._update_table(results, f"Поиск: {text}")
        elif not text:
            self.load_all_documents()

    def update_title(self, title):
        """Обновление заголовка"""
        if hasattr(self, 'labelTitle'):
            self.labelTitle.setText(title)
        self.current_title = title

    def get_documents_table(self):
        """Получение объекта таблицы"""
        return self.documents_table

    def refresh(self):
        """Обновить текущие данные"""
        if self.current_type_id is not None:
            self.load_documents_by_type(self.current_type_id)
        elif self.current_direction is not None:
            self.load_documents_by_direction(self.current_direction)
        else:
            self.load_all_documents()




if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DocumentsPanel()
    window.setWindowTitle("Documents Panel Test")
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec())