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

    # ---------- остальное без изменений ----------

    def create_employees_tab(self):
        """Создание вкладки сотрудников"""
        self.employees_page = EmployeesPage(http_client=self.http_client)
        self.tabWidget.addTab(self.employees_page, "Сотрудники")

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
        """Загрузка всех данных"""
        print("Загрузка данных...")

        # Создаем вкладки
        self.create_employees_tab()
        self.create_tags_tab()
        self.create_document_types_tab()
        self.create_organizations_tab()
        self.create_structure_tabs()

        print("Все данные загружены!")

    def create_tags_tab(self):
        """Создание вкладки тегов"""
        self.tags_page = TagsPage()
        self.tabWidget.addTab(self.tags_page, "Теги")

    def create_document_types_tab(self):
        """Создание вкладки типов документов"""
        self.document_types_page = DocumentTypesPage()
        self.tabWidget.addTab(self.document_types_page, "Типы документов")

    def create_organizations_tab(self):
        """Создание вкладки организаций"""
        self.organizations_page = OrganizationsPage()
        self.tabWidget.addTab(self.organizations_page, "Организации")

    def create_structure_tabs(self):
        """Вкладка «Структура»: организации и подразделения из API"""
        self.structure_page = StructurePage(parent=self, http_client=self.http_client)
        self.tabWidget.addTab(self.structure_page, "Структура")


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
