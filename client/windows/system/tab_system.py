import os
import sys

from PyQt6 import uic
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from client.core.state.app_state import AppState
from client.core.themes import apply_theme_to_widget
from client.windows.system.document_types.document_type_page import DocumentTypesPage
from client.windows.system.employees.employee_page import EmployeesPage
from client.windows.system.organizations.organization_page import OrganizationsPage
from client.windows.system.structure.structure_page import StructurePage
from client.windows.system.tags.tag_page import TagsPage


class SystemTab(QWidget):
    """Основной виджет вкладки Система"""

    def __init__(self, parent=None):  # ← добавили параметр
        super().__init__(parent)

        self.http_client = AppState().http_client  # ← сохранили

        self.tabWidget = None
        self.employees_page = None
        self.tags_page = None
        self.document_types_page = None
        self.organizations_page = None
        self.structure_page = None

        self.init_ui_from_file()
        self.load_all_data()

    # ---------- ленивое создание вкладок ----------
    # Конструкторы страниц сразу ходят в API (сотрудники, теги, типы, организации,
    # структура ~100 запросов). Поэтому на старте добавляем пустые заглушки,
    # а настоящая страница создаётся при первом открытии вкладки.

    def init_ui_from_file(self):
        """Загрузка UI из файла tab_system.ui"""
        ui_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "ui",
            "system",
            "tab_system.ui",
        )

        uic.loadUi(ui_file_path, self)
        apply_theme_to_widget(self)

        self.tabWidget = self.findChild(QTabWidget, "tabWidget")

    def load_all_data(self):
        """Добавляет вкладки-заглушки; данные грузятся при первом открытии вкладки."""
        self._lazy_tabs = {}  # заглушка -> (атрибут, заголовок, фабрика)
        self._pages_linked = False

        tabs = (
            ("employees_page", "Сотрудники", lambda: EmployeesPage(http_client=self.http_client)),
            ("tags_page", "Теги", lambda: TagsPage()),
            ("document_types_page", "Типы документов", lambda: DocumentTypesPage()),
            ("organizations_page", "Организации", lambda: OrganizationsPage()),
            ("structure_page", "Структура", lambda: StructurePage(parent=self, http_client=self.http_client)),
        )
        for attr, title, factory in tabs:
            placeholder = QWidget()
            self._lazy_tabs[placeholder] = (attr, title, factory)
            self.tabWidget.addTab(placeholder, title)

        self.tabWidget.currentChanged.connect(self._ensure_page)
        self._ensure_page(self.tabWidget.currentIndex())  # текущая (первая) вкладка нужна сразу

    def _ensure_page(self, index: int):
        """Создаёт настоящую страницу вместо заглушки, если её ещё нет."""
        if index < 0:
            return
        placeholder = self.tabWidget.widget(index)
        entry = self._lazy_tabs.pop(placeholder, None)
        if entry is None:
            return  # страница уже создана

        attr, title, factory = entry
        page = factory()
        setattr(self, attr, page)

        was_blocked = self.tabWidget.blockSignals(True)
        try:
            self.tabWidget.removeTab(index)
            placeholder.deleteLater()
            self.tabWidget.insertTab(index, page, title)
            self.tabWidget.setCurrentIndex(index)
        finally:
            self.tabWidget.blockSignals(was_blocked)

        self._link_pages()

    def _link_pages(self):
        """«Сотрудники» и «Структура» показывают одни и те же данные — держим в синхроне,
        как только созданы обе страницы (если одной нет, она при создании загрузит свежие данные)."""
        if self._pages_linked or self.employees_page is None or self.structure_page is None:
            return
        self._pages_linked = True
        self.employees_page.employees_changed.connect(self.structure_page.reload_employees)
        self.structure_page.structure_changed.connect(lambda: self.employees_page.load_employees(notify=False))


class MainWindow(QMainWindow):
    """Главное окно приложения"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Система управления МАЗ")
        self.setGeometry(100, 100, 1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.system_tab = SystemTab()
        layout.addWidget(self.system_tab)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    print("Приложение запущено")
    sys.exit(app.exec())