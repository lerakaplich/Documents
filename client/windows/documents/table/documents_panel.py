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

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, QTimer, pyqtSignal, Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox, QWidget
from PyQt6.uic import loadUi

from client.core.state.app_state import AppState
from client.core.table.documents_panel_controller import DocumentsPanelController, SORT_FIELDS
from client.core.themes import apply_theme_to_widget, get_manager
from client.services.doc_type_service import doc_type_events
from client.windows.animations.floating_action_button import FloatingActionButton
from client.windows.documents.table.documents_pagination_manager import (
    DocumentsPaginationManager,
)
from client.windows.documents.table.documents_panel_columns import (
    DocumentsColumnController,
)
from client.windows.documents.table.documents_panel_crud import DocumentsCrudController
from client.windows.documents.table.documents_panel_filters import (
    DocumentsFilterController,
)
from client.windows.documents.table.documents_panel_row_actions import (
    DocumentsRowActionController,
)
from client.windows.documents.table.documents_table import DocumentsTable
from client.windows.documents.table.sort_icons import sort_icon

ROOT_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
)


class _LoadSignals(QObject):
    """Сигналы фоновой загрузки (доставляются в поток интерфейса)."""

    done = pyqtSignal(int, object)  # token, результат контроллера
    failed = pyqtSignal(int, str)  # token, текст ошибки


class _LoadTask(QRunnable):
    """Блокирующий вызов контроллера (HTTP) — вне потока интерфейса."""

    def __init__(self, token, fn, is_current, signals):
        super().__init__()
        self._token = token
        self._fn = fn
        self._is_current = is_current
        self._signals = signals

    def run(self):
        if not self._is_current(self._token):
            return  # пока задача стояла в очереди, пользователь запросил другое
        try:
            result = self._fn()
        except Exception as e:  # noqa: BLE001
            self._signals.failed.emit(self._token, str(e))
            return
        self._signals.done.emit(self._token, result)


class _FuncTask(QRunnable):
    """Фоновая задача «выстрелил и забыл» (без результата)."""

    def __init__(self, fn):
        super().__init__()
        self._fn = fn

    def run(self):
        try:
            self._fn()
        except Exception as e:  # noqa: BLE001
            print(f"[DocumentsPanel] фоновая задача: {e}")


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

        # Загрузка списков идёт в фоне. Поток один: контроллер хранит состояние
        # (тип/страница/сортировка), поэтому запросы выстраиваются в очередь,
        # а результаты устаревших запросов отбрасываются (см. _load_async).
        self._load_pool = QThreadPool(self)
        self._load_pool.setMaxThreadCount(1)
        self._aux_pool = QThreadPool(self)  # типы документов — отдельно, не задерживая таблицу
        self._aux_pool.setMaxThreadCount(1)
        self._load_token = 0
        self._load_after = None
        self._load_signals = _LoadSignals(self)
        self._load_signals.done.connect(self._on_load_done)
        self._load_signals.failed.connect(self._on_load_failed)
        self._sort_icon_cache = {}

        self._init_ui()
        self._init_table()

        # Помощники — каждый привязан к этой панели (см. докстринг файла)
        self.columns = DocumentsColumnController(self)
        self.filters = DocumentsFilterController(self)
        self.crud = DocumentsCrudController(self)
        self.row_actions = DocumentsRowActionController(self)

        # Тип документа создан/изменён/удалён → перечитать типы и перестроить таблицу
        doc_type_events.types_changed.connect(self._on_types_changed)

        if hasattr(self, "statsBtn"):
            self.statsBtn.clicked.connect(self._show_unanswered_stats)
        if hasattr(self, "searchEdit"):
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
        if hasattr(self, "contentFrame"):
            target_layout = self.contentLayout
        elif hasattr(self, "horizontalLayoutHeader"):
            target_layout = self.verticalLayout
        elif hasattr(self, "panelLayout"):
            target_layout = self.panelLayout
        else:
            target_layout = self.layout()
        target_layout.addWidget(self.documents_table)

        # Панель пагинации — сразу под таблицей
        self.pagination = DocumentsPaginationManager()
        self.pagination.setup_bar(target_layout, self._change_page)

        # Сортировка по клику на заголовок — на сервере, локальную выключаем
        table = self.documents_table.tableWidget
        table.setSortingEnabled(False)
        header = table.horizontalHeader()
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._on_header_clicked)

    def _update_floating_button(self):
        """«+» (создание документа) недоступна в архиве."""
        if hasattr(self, "floating_btn"):
            self.floating_btn.setVisible(self.controller.current_view_mode != "archive")

    def on_scroll(self, value):
        if self.controller.current_view_mode == "archive":
            return
        if hasattr(self, "floating_btn"):
            self.floating_btn.hide_with_animation()
            self.floating_btn.start_hide_timer()

    def _update_table(
        self,
        documents: list,
        doc_type: str | None = None,
        title: str | None = None,
        view_mode: str | None = None,
    ):
        """Обновить UI-компонент таблицы. Вызывается и помощниками
        (columns/filters), поэтому остаётся в самой панели."""
        try:
            doc_type = doc_type or "default"
            view_mode = view_mode or self.controller.current_view_mode or "all"

            self.documents_table._controller.switch_doc_type(doc_type, documents, view_mode)

            if title and hasattr(self, "labelTitle"):
                self.labelTitle.setText(title)

            self.pagination.update(self.controller.pagination)
            self.columns.apply_layout()
            self._update_sort_indicator()
            self._update_floating_button()

        except Exception as e:
            print(f"[DocumentsPanel] Error updating table: {e}")
            import traceback

            traceback.print_exc()

    def _on_header_clicked(self, col: int):
        """Клик по заголовку столбца → серверная сортировка."""
        item = self.documents_table.tableWidget.horizontalHeaderItem(col)
        if item is None:
            return
        column_title = item.text()
        if column_title not in SORT_FIELDS:
            return  # по этому столбцу сортировка не поддерживается
        self._load_async(
            lambda: self.controller.toggle_sort(column_title),
            after=lambda docs: self.documents_table.tableWidget.scrollToTop(),
        )

    def _update_sort_indicator(self):
        """Иконки сортировки в заголовках: ⇅ у сортируемых, ▲/▼ у активного."""
        table = self.documents_table.tableWidget
        header = table.horizontalHeader()
        header.setSortIndicatorShown(False)  # системная стрелка не нужна

        color = get_manager().current.TABLE_HEADER_TEXT
        active = self.controller.sort_by
        asc = self.controller.sort_order == "asc"

        for col in range(table.columnCount()):
            item = table.horizontalHeaderItem(col)
            if item is None:
                continue
            field = SORT_FIELDS.get(item.text())
            if field is None:
                item.setIcon(QIcon())
                continue
            kind = ("asc" if asc else "desc") if field == active else "none"
            key = (kind, str(color))
            icon = self._sort_icon_cache.get(key)
            if icon is None:
                icon = self._sort_icon_cache[key] = sort_icon(kind, color)
            item.setIcon(icon)
        header.viewport().update()

    def reapply_theme(self):
        apply_theme_to_widget(self)
        self.pagination.reapply_theme()
        self._update_sort_indicator()

    def _init_floating_button(self):
        self.floating_btn = FloatingActionButton(self)
        self.floating_btn.clicked.connect(self.crud.open_create_dialog)
        if hasattr(self.documents_table, "tableWidget"):
            scrollbar = self.documents_table.tableWidget.verticalScrollBar()
            scrollbar.valueChanged.connect(self.on_scroll)
        self.position_floating_button()

    def _show_unanswered_stats(self):
        """Открывает диалог со статистикой по неотвеченным документам."""
        from client.services.document_service import DocumentService
        from client.windows.documents.stats.unanswered_stats_dialog import (
            UnansweredStatsDialog,
        )

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
        if hasattr(self, "floating_btn"):
            margin = 30
            x = self.width() - self.floating_btn.width() - margin
            y = self.height() - self.floating_btn.height() - margin
            self.floating_btn.update_base_position(x, y)
            self.floating_btn.raise_()

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

    def _load_async(self, fn, after=None):
        """Выполняет fn (вызов контроллера, возвращает (documents, title, view_mode,
        doc_type) или None) в фоне и обновляет таблицу, когда ответ пришёл.
        Если за время ожидания пользователь запросил другое — результат отбрасывается."""
        self._load_token += 1
        token = self._load_token
        self._load_after = after
        self.setCursor(Qt.CursorShape.BusyCursor)

        def job():
            result = fn()
            if result is not None:
                self._warm_type_fields(result[3])  # поля типа — тоже в фоне, а не при отрисовке
            return result

        self._load_pool.start(_LoadTask(token, job, lambda t: t == self._load_token, self._load_signals))

    def _warm_type_fields(self, settings_key):
        """Подгружает поля типа в кэш таблицы (иначе GET на каждый новый тип
        уходит из потока интерфейса при построении столбцов)."""
        if str(settings_key).isdigit():
            try:
                self.documents_table._controller._get_type_fields(int(settings_key))
            except Exception as e:  # noqa: BLE001
                print(f"[DocumentsPanel] не удалось прогреть поля типа: {e}")

    def _on_load_done(self, token: int, result):
        if token != self._load_token:
            return  # устаревший ответ
        self.unsetCursor()
        after, self._load_after = self._load_after, None
        if result is None:
            return
        documents, title, view_mode, doc_type = result
        self._update_table(documents, doc_type, title, view_mode)
        if after is not None:
            after(documents)

    def _on_load_failed(self, token: int, message: str):
        if token != self._load_token:
            return
        self.unsetCursor()
        self._load_after = None
        print(f"[DocumentsPanel] Ошибка загрузки: {message}")

    def load_all_documents(self):
        """Запросить данные у контроллера и отобразить их"""
        self._load_async(
            self.controller.load_all_documents,
            after=lambda docs: self.data_loaded.emit(len(docs)),
        )

    def load_documents_by_type(self, type_id: int, type_name: str | None = None, direction: str | None = None):
        # Типы с полями обновляем фоном (для диалога создания) — таблицу это не задерживает
        self._aux_pool.start(_FuncTask(self.controller.refresh_doc_types))

        def after(docs):
            self.type_changed.emit(type_id)
            self.data_loaded.emit(len(docs))

        self._load_async(
            lambda: self.controller.load_documents_by_type(type_id, type_name, direction),
            after=after,
        )

    def load_documents_by_direction(self, direction: str, title: str | None = None):
        def after(docs):
            self.direction_changed.emit(direction)
            self.data_loaded.emit(len(docs))

        self._load_async(
            lambda: self.controller.load_documents_by_direction(direction, title),
            after=after,
        )

    def load_archived_documents(self):
        """Загружает архивные документы текущего пользователя (scope='archive')."""
        self._load_async(
            self.controller.load_archived_documents,
            after=lambda docs: self.data_loaded.emit(len(docs)),
        )

    def _change_page(self, delta: int):
        """◀ / ▶ в панели пагинации."""
        p = self.controller.pagination
        if not 1 <= p["page"] + delta <= p["pages"]:
            return
        self._load_async(
            lambda: self.controller.change_page(delta),
            after=lambda docs: self.documents_table.tableWidget.scrollToTop(),
        )

    def _on_types_changed(self):
        """Типы документов изменились (поля, список) — обновляем кэш типов и таблицу."""
        try:
            # типы и страница — один фоновый запрос, интерфейс не замирает
            self._load_async(lambda: (self.controller.refresh_doc_types(), self.controller.refresh())[1])
        except Exception as e:
            print(f"[DocumentsPanel] Error on types_changed: {e}")

    def refresh(self):
        """Перезагрузить текущую страницу через контроллер"""
        documents, title, view_mode, doc_type = self.controller.refresh()
        self._update_table(documents, doc_type, title, view_mode)

    def refresh_async(self):
        """То же, что refresh(), но без блокировки интерфейса."""
        self._load_async(self.controller.refresh)

    # ========== ПОИСК ==========

    def on_search_changed(self, text):
        self.search_requested.emit(text)
        self._pending_search = text
        self._search_timer.start()  # перезапуск: запрос уйдёт после паузы в наборе

    def _run_search(self):
        query = self._pending_search
        self._load_async(lambda: self.controller.search_documents(query))

    # ========== ТЕМА / ПРОЧЕЕ ==========


    def update_title(self, title):
        if hasattr(self, "labelTitle"):
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