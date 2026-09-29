"""
Панель документов - управление данными и UI.

Разбит на несколько файлов, чтобы не раздувать один класс:
  - documents_panel_columns.py      — меню «Столбцы» + сохранение раскладки
  - documents_panel_filters.py      — меню «Фильтр»/«Статусы» + диалог периода
  - documents_panel_crud.py         — создание/редактирование документа
  - documents_panel_row_actions.py  — действия из контекстного меню строки
Сама панель отвечает за UI-каркас, загрузку данных через контроллер и
проксирование сигналов между таблицей и этими помощниками. Каждый помощник
хранит ссылку на панель (`panel`) и обращается к её виджетам/контроллеру
напрямую — отдельного протокола между ними нет, это сознательный компромисс
ради простоты (как у RowManager/ColumnManager, которые так же координируют
свои под-менеджеры).
"""
import os
import sys
from PyQt6.QtWidgets import QWidget, QApplication, QMessageBox
from PyQt6.QtCore import pyqtSignal, QTimer
from PyQt6.uic import loadUi

from client.core.state.app_state import AppState
from client.core.themes import apply_theme_to_widget
from client.windows.documents.table.documents_table import DocumentsTable
from client.windows.documents.table.documents_pagination_manager import DocumentsPaginationManager
from client.windows.documents.table.documents_panel_columns import DocumentsColumnController
from client.windows.documents.table.documents_panel_filters import DocumentsFilterController
from client.windows.documents.table.documents_panel_crud import DocumentsCrudController
from client.windows.documents.table.documents_panel_row_actions import DocumentsRowActionController
from client.core.table.documents_panel_controller import DocumentsPanelController

from client.windows.animations.floating_action_button import FloatingActionButton

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


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

        # HTTP-клиент — нужен для загрузки реальных данных в диалогах
        self.http_client = AppState().http_client
        print(f"[DocumentsPanel] http_client = {self.http_client}")

        # Контроллер бизнес-логики (реальные документы идут через http_client)
        self.controller = DocumentsPanelController(self.http_client)

        # Поиск идёт на сервер — не шлём запрос на каждую букву
        self._pending_search = ""
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(350)
        self._search_timer.timeout.connect(self._run_search)

        self._init_ui()
        self._init_table()

        # Помощники — каждый привязан к этой панели (см. докстринг файла)
        self.columns = DocumentsColumnController(self)
        self.filters = DocumentsFilterController(self)
        self.crud = DocumentsCrudController(self)
        self.row_actions = DocumentsRowActionController(self)

        if hasattr(self, 'statsBtn'):
            self.statsBtn.clicked.connect(self._show_unanswered_stats)
        if hasattr(self, 'searchEdit'):
            self.searchEdit.textChanged.connect(self.on_search_changed)

        self._connect_signals()
        self._init_floating_button()

        # Загружаем все документы по умолчанию
        self.load_all_documents()
        self.documents_table.document_action_triggered.connect(self._on_document_action)

    # ========== UI ==========

    def _init_ui(self):
        ui_path = os.path.join(ROOT_DIR, "client", "ui", "documents", "table", "documents_panel.ui")
        loadUi(ui_path, self)
        apply_theme_to_widget(self)

    def _init_table(self):
        self.documents_table = DocumentsTable(http_client=self.http_client)
        if hasattr(self, 'contentFrame'):
            target_layout = self.contentLayout
        elif hasattr(self, 'horizontalLayoutHeader'):
            target_layout = self.verticalLayout
        elif hasattr(self, 'panelLayout'):
            target_layout = self.panelLayout
        else:
            target_layout = self.layout()
        target_layout.addWidget(self.documents_table)

        # Панель пагинации — сразу под таблицей
        self.pagination = DocumentsPaginationManager()
        self.pagination.setup_bar(target_layout, self._change_page)

    def _init_floating_button(self):
        self.floating_btn = FloatingActionButton(self)
        self.floating_btn.clicked.connect(self.crud.open_create_dialog)
        if hasattr(self.documents_table, 'tableWidget'):
            scrollbar = self.documents_table.tableWidget.verticalScrollBar()
            scrollbar.valueChanged.connect(self.on_scroll)
        self.position_floating_button()

    def _show_unanswered_stats(self):
        """Открывает диалог со статистикой по неотвеченным документам."""
        from client.services.document_service import DocumentService
        from client.windows.documents.stats.unanswered_stats_dialog import UnansweredStatsDialog

        try:
            service = DocumentService(self.http_client)
            stats = service.get_unanswered_stats()
            UnansweredStatsDialog(stats, parent=self).exec()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить статистику: {e}")

    def _connect_signals(self):
        self.documents_table.document_action_triggered.connect(self.document_action_triggered.emit)
        self.documents_table.read_status_changed.connect(
            lambda doc_id, is_read: print(f"Document {doc_id} read: {is_read}")
        )
        self.documents_table.pin_status_changed.connect(self.pin_status_changed.emit)
        self.documents_table.data_loaded.connect(self.data_loaded.emit)

    # ========== ЛОГИКА ПЛАВАЮЩЕЙ КНОПКИ ==========

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
        """Оставлен как тонкая обёртка — вдруг что-то снаружи ещё вызывает
        именно этот метод, а не floating_btn.clicked напрямую."""
        self.crud.open_create_dialog()

    def on_document_created(self, document_data: dict):
        """Оставлен для обратной совместимости — см. DocumentsCrudController.create_document."""
        self.crud.create_document(document_data)

    # ========== ЗАГРУЗКА И ОТОБРАЖЕНИЕ ДАННЫХ ==========

    def load_all_documents(self):
        """Запросить данные у контроллера и отобразить их"""
        documents, title, view_mode, doc_type = self.controller.load_all_documents()
        self._update_table(documents, doc_type, title, view_mode)
        self.data_loaded.emit(len(documents))

    def load_documents_by_type(self, type_id: int, type_name: str = None, direction: str = None):
        documents, title, view_mode, doc_type = self.controller.load_documents_by_type(
            type_id, type_name, direction)
        self._update_table(documents, doc_type, title, view_mode)
        self.type_changed.emit(type_id)
        self.data_loaded.emit(len(documents))

    def load_documents_by_direction(self, direction: str, title: str = None):
        documents, title, view_mode, doc_type = self.controller.load_documents_by_direction(direction, title)
        self._update_table(documents, doc_type, title, view_mode)
        self.direction_changed.emit(direction)
        self.data_loaded.emit(len(documents))

    def load_archived_documents(self):
        """Загружает архивные документы текущего пользователя (scope='archive')."""
        self.controller.set_filters(scope="archive")
        documents, title, view_mode, doc_type = self.controller._load_current(1)
        self._update_table(documents, doc_type, "Архив", view_mode)
        self.data_loaded.emit(len(documents))

    def _update_table(self, documents: list, doc_type: str = None, title: str = None, view_mode: str = None):
        """Обновить UI-компонент таблицы. Вызывается и помощниками
        (columns/filters), поэтому остаётся в самой панели, а не переезжает
        вместе с ними — это единственная точка, которая реально трогает
        таблицу, пагинацию и раскладку столбцов разом."""
        try:
            doc_type = doc_type or "default"
            view_mode = view_mode or self.controller.current_view_mode or "all"

            self.documents_table._controller.switch_doc_type(doc_type, documents, view_mode)

            if title and hasattr(self, 'labelTitle'):
                self.labelTitle.setText(title)

            self.pagination.update(self.controller.pagination)
            self.columns.apply_layout()

        except Exception as e:
            print(f"[DocumentsPanel] Error updating table: {e}")
            import traceback
            traceback.print_exc()

    def _change_page(self, delta: int):
        """◀ / ▶ в панели пагинации."""
        p = self.controller.pagination
        if not 1 <= p['page'] + delta <= p['pages']:
            return
        documents, title, view_mode, doc_type = self.controller.change_page(delta)
        self._update_table(documents, doc_type, title, view_mode)
        self.documents_table.tableWidget.scrollToTop()

    def refresh(self):
        """Перезагрузить текущую страницу через контроллер"""
        documents, title, view_mode, doc_type = self.controller.refresh()
        self._update_table(documents, doc_type, title, view_mode)

    # ========== ПОИСК ==========

    def on_search_changed(self, text):
        self.search_requested.emit(text)
        self._pending_search = text
        self._search_timer.start()  # перезапуск: запрос уйдёт после паузы в наборе

    def _run_search(self):
        documents, title, view_mode, doc_type = self.controller.search_documents(self._pending_search)
        self._update_table(documents, doc_type, title, view_mode)

    # ========== ТЕМА / ПРОЧЕЕ ==========

    def reapply_theme(self):
        apply_theme_to_widget(self)
        self.pagination.reapply_theme()

    def update_title(self, title):
        if hasattr(self, 'labelTitle'):
            self.labelTitle.setText(title)
        self.controller.current_title = title

    def get_documents_table(self):
        return self.documents_table

    # ========== ДЕЙСТВИЯ НАД ДОКУМЕНТОМ ==========

    def _on_document_action(self, action_type: str, document_data: dict):
        """Диспетчеризация — вся реальная логика в DocumentsRowActionController."""
        self.row_actions.handle(action_type, document_data)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DocumentsPanel()
    window.setWindowTitle("Documents Panel Test")
    window.resize(1200, 800)
    window.show()
    sys.exit(app.exec())