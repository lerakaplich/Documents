import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QGridLayout, QSpacerItem, QSizePolicy, QApplication,
    QMainWindow, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6 import uic

from client.core import http_client
from client.core.state.app_state import AppState
from client.core.themes import apply_theme_to_widget
from client.windows.animations.collapsible_group import CollapsibleGroup
from client.windows.system.departments.department_card import DepartmentCard
from client.windows.system.departments.department_page import DepartmentPage
from client.windows.system.document_types.document_type_page import DocumentTypesPage
from client.windows.system.employees.employee_page import EmployeesPage
from client.windows.system.organizations.organization_page import OrganizationsPage
from client.windows.system.tags.tag_page import TagsPage


class SystemTab(QWidget):
    """Основной виджет вкладки Система"""

    def __init__(self, parent=None):   # ← добавили параметр
        super().__init__(parent)

        self.http_client = AppState().http_client              # ← сохранили

        self.tabWidget = None
        self.structure_data = []
        self.employees_page = None
        self.tags_page = None
        self.document_types_page = None
        self.organizations_page = None
        self.structure_pages = {}
        self.structure_tab_names = {}

        self.department_types = {}

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
            "ui", "system", "tab_system.ui"
        )

        uic.loadUi(ui_file_path, self)
        apply_theme_to_widget(self)

        self.tabWidget = self.findChild(QTabWidget, "tabWidget")

    def load_all_data(self):
        """Загрузка всех данных"""
        print("Загрузка тестовых данных...")

        # Загружаем типы отделов (в реальном приложении из БД)
        self.load_department_types()

        self.structure_data = [
            {
                "id": 1,
                "name": "ОАО МАЗ",
                "children": [
                    {
                        "id": 2,
                        "name": "Дирекция",
                        "children": [
                            {
                                "id": 3,
                                "name": "Управление информационных технологий (УИТ)",
                                "department_type_id": 1,  # ← Добавляем ID типа отдела
                                "children": [
                                    {
                                        "id": 4,
                                        "name": "Отдел разработки СЭД",
                                        "department_type_id": 2,  # ← Добавляем ID типа отдела
                                        "children": []
                                    },
                                    {
                                        "id": 5,
                                        "name": "Отдел системного администрирования",
                                        "department_type_id": 2,  # ← Добавляем ID типа отдела
                                        "children": []
                                    }
                                ]
                            },
                            {
                                "id": 6,
                                "name": "Канцелярия (Общий отдел)",
                                "department_type_id": 2,  # ← Добавляем ID типа отдела
                                "children": []
                            },
                            {
                                "id": 7,
                                "name": "Планово-экономический отдел",
                                "department_type_id": 2,  # ← Добавляем ID типа отдела
                                "children": [
                                    {
                                        "id": 8,
                                        "name": "Бюро планирования",
                                        "department_type_id": 3,  # ← Добавляем ID типа отдела
                                        "children": []
                                    },
                                    {
                                        "id": 9,
                                        "name": "Бюро анализа",
                                        "department_type_id": 3,  # ← Добавляем ID типа отдела
                                        "children": []
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        "id": 10,
                        "name": "Техническая дирекция",
                        "children": [
                            {
                                "id": 11,
                                "name": "Конструкторский отдел",
                                "department_type_id": 2,  # ← Добавляем ID типа отдела
                                "children": [
                                    {
                                        "id": 12,
                                        "name": "Сектор двигателей",
                                        "department_type_id": 4,  # ← Добавляем ID типа отдела
                                        "children": []
                                    },
                                    {
                                        "id": 13,
                                        "name": "Сектор трансмиссий",
                                        "department_type_id": 4,  # ← Добавляем ID типа отдела
                                        "children": []
                                    }
                                ]
                            },
                            {
                                "id": 14,
                                "name": "Технологический отдел",
                                "department_type_id": 2,  # ← Добавляем ID типа отдела
                                "children": []
                            },
                            {
                                "id": 15,
                                "name": "Цех сборки №1",
                                "department_type_id": 5,  # ← Добавляем ID типа отдела
                                "children": []
                            },
                            {
                                "id": 16,
                                "name": "Цех сборки №2",
                                "department_type_id": 5,  # ← Добавляем ID типа отдела
                                "children": []
                            }
                        ]
                    },
                    {
                        "id": 17,
                        "name": "Финансовая дирекция",
                        "children": [
                            {
                                "id": 18,
                                "name": "Бухгалтерия",
                                "department_type_id": 2,  # ← Добавляем ID типа отдела
                                "children": []
                            },
                            {
                                "id": 19,
                                "name": "Финансовый отдел",
                                "department_type_id": 2,  # ← Добавляем ID типа отдела
                                "children": []
                            }
                        ]
                    },
                    {
                        "id": 20,
                        "name": "Управление персоналом",
                        "children": [
                            {
                                "id": 21,
                                "name": "Отдел кадров",
                                "department_type_id": 2,  # ← Добавляем ID типа отдела
                                "children": []
                            },
                            {
                                "id": 22,
                                "name": "Отдел охраны труда",
                                "department_type_id": 2,  # ← Добавляем ID типа отдела
                                "children": []
                            }
                        ]
                    }
                ]
            },
            {
                "id": 23,
                "name": "ООО МАЗ-Кузовной",
                "children": [
                    {
                        "id": 24,
                        "name": "Дирекция",
                        "children": []
                    },
                    {
                        "id": 25,
                        "name": "Производственная дирекция",
                        "children": [
                            {
                                "id": 26,
                                "name": "Технический отдел",
                                "department_type_id": 2,  # ← Добавляем ID типа отдела
                                "children": []
                            },
                            {
                                "id": 27,
                                "name": "Производственный отдел",
                                "department_type_id": 2,  # ← Добавляем ID типа отдела
                                "children": []
                            },
                            {
                                "id": 28,
                                "name": "Цех кузовной",
                                "department_type_id": 5,  # ← Добавляем ID типа отдела
                                "children": []
                            }
                        ]
                    }
                ]
            },
            {
                "id": 29,
                "name": "СООО МАЗ-МАН",
                "children": [
                    {
                        "id": 30,
                        "name": "Дирекция",
                        "children": []
                    },
                    {
                        "id": 31,
                        "name": "Техническая дирекция",
                        "children": [
                            {
                                "id": 32,
                                "name": "Отдел разработок",
                                "department_type_id": 2,  # ← Добавляем ID типа отдела
                                "children": []
                            },
                            {
                                "id": 33,
                                "name": "Проектный отдел",
                                "department_type_id": 2,  # ← Добавляем ID типа отдела
                                "children": []
                            }
                        ]
                    }
                ]
            }
        ]

        self.analyze_structure_types()

        # Создаем вкладки
        self.create_employees_tab()
        self.create_tags_tab()
        self.create_document_types_tab()
        self.create_organizations_tab()
        self.create_structure_tabs()

        print("Все данные загружены!")

    def load_department_types(self):
        """Загрузка типов отделов (в реальном приложении из БД)"""
        # В реальном приложении здесь будет запрос к БД:
        # self.department_types = {dt.id: dt.name for dt in session.query(DepartmentType).all()}

        # Тестовые данные
        self.department_types = {
            1: "Управления",
            2: "Отделы",
            3: "Бюро",
            4: "Сектора",
            5: "Цеха",
        }

    def analyze_structure_types(self):
        """Анализирует структуру и определяет уникальные названия уровней для вкладок"""
        self.structure_tab_names = {}

        def traverse(node, level=0):
            if node.get("children"):
                child_names = [child["name"] for child in node["children"]]
                level_type = self.detect_level_type(child_names)

                if level_type not in self.structure_tab_names:
                    self.structure_tab_names[level_type] = {
                        "level": level,
                        "name": self.get_type_display_name(level_type)
                    }

                for child in node["children"]:
                    traverse(child, level + 1)

        for org in self.structure_data:
            traverse(org, 0)

    def detect_level_type(self, names):
        """Определяет тип уровня по названиям подразделений"""
        all_names = " ".join(names).lower()

        if any(word in all_names for word in ["цех", "цеха"]):
            return "workshops"
        elif any(word in all_names for word in ["отдел", "отделы"]):
            return "departments"
        elif any(word in all_names for word in ["управление", "управления"]):
            return "divisions"
        elif any(word in all_names for word in ["бюро"]):
            return "bureaus"
        elif any(word in all_names for word in ["сектор", "сектора"]):
            return "sections"
        elif any(word in all_names for word in ["филиал", "филиалы"]):
            return "branches"
        elif any(word in all_names for word in ["дирекция", "дирекции"]):
            return "directorates"
        elif any(word in all_names for word in ["департамент", "департаменты"]):
            return "departments"
        else:
            return "departments"

    def get_type_display_name(self, type_key):
        """Возвращает русское название для типа структуры"""
        names = {
            "divisions": "Подразделения",
            "departments": "Отделы",
            "workshops": "Цеха",
            "branches": "Филиалы",
            "sections": "Сектора",
            "bureaus": "Бюро",
            "directorates": "Дирекции",
        }
        return names.get(type_key, type_key.capitalize())


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

    # В методе create_structure_tabs замените:

    def create_structure_tabs(self):
        """Создание единой вкладки для структуры с иерархическим отображением"""
        # Создаем одну страницу со всей структурой
        page = DepartmentPage(
            parent=self,
            structure_data=self.structure_data
        )
        self.tabWidget.addTab(page, "Структура")


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