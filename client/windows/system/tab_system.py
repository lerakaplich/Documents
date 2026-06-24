import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QGridLayout, QSpacerItem, QSizePolicy, QApplication,
    QMainWindow, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6 import uic

from client.windows.animations.collapsible_group import CollapsibleGroup
from client.windows.system.departments.department_card import DepartmentCard
from client.windows.system.departments.department_page import DepartmentPage
from client.windows.system.document_types.document_type_page import DocumentTypesPage
from client.windows.system.employees.employee_page import EmployeesPage
from client.windows.system.organizations.organization_page import OrganizationsPage
from client.windows.system.tags.tag_page import TagsPage


class SystemTab(QWidget):
    """Основной виджет вкладки Система"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.tabWidget = None
        self.structure_data = []
        self.employees_page = None
        self.tags_page = None
        self.document_types_page = None
        self.organizations_page = None
        self.structure_pages = {}  # ← ДОБАВИТЬ ЭТУ СТРОКУ

        self.structure_tab_names = {}

        self.init_ui_from_file()
        self.load_all_data()

    def init_ui_from_file(self):
        """Загрузка UI из файла tab_system.ui"""
        ui_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "ui", "system", "tab_system.ui"
        )

        uic.loadUi(ui_file_path, self)

        self.tabWidget = self.findChild(QTabWidget, "tabWidget")

    def load_all_data(self):
        """Загрузка всех данных"""
        print("Загрузка тестовых данных...")

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
                                "children": [
                                    {
                                        "id": 4,
                                        "name": "Отдел разработки СЭД",
                                        "children": []
                                    },
                                    {
                                        "id": 5,
                                        "name": "Отдел системного администрирования",
                                        "children": []
                                    }
                                ]
                            },
                            {
                                "id": 6,
                                "name": "Канцелярия (Общий отдел)",
                                "children": []
                            },
                            {
                                "id": 7,
                                "name": "Планово-экономический отдел",
                                "children": [
                                    {
                                        "id": 8,
                                        "name": "Бюро планирования",
                                        "children": []
                                    },
                                    {
                                        "id": 9,
                                        "name": "Бюро анализа",
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
                                "children": [
                                    {
                                        "id": 12,
                                        "name": "Сектор двигателей",
                                        "children": []
                                    },
                                    {
                                        "id": 13,
                                        "name": "Сектор трансмиссий",
                                        "children": []
                                    }
                                ]
                            },
                            {
                                "id": 14,
                                "name": "Технологический отдел",
                                "children": []
                            },
                            {
                                "id": 15,
                                "name": "Цех сборки №1",
                                "children": []
                            },
                            {
                                "id": 16,
                                "name": "Цех сборки №2",
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
                                "children": []
                            },
                            {
                                "id": 19,
                                "name": "Финансовый отдел",
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
                                "children": []
                            },
                            {
                                "id": 22,
                                "name": "Отдел охраны труда",
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
                                "children": []
                            },
                            {
                                "id": 27,
                                "name": "Производственный отдел",
                                "children": []
                            },
                            {
                                "id": 28,
                                "name": "Цех кузовной",
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
                                "children": []
                            },
                            {
                                "id": 33,
                                "name": "Проектный отдел",
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

    def create_employees_tab(self):
        """Создание вкладки сотрудников"""
        self.employees_page = EmployeesPage()
        self.tabWidget.addTab(self.employees_page, "Сотрудники")

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
        """Создание динамических вкладок на основе проанализированной структуры"""
        sorted_types = sorted(self.structure_tab_names.items(),
                              key=lambda x: x[1]["level"])

        for type_key, type_info in sorted_types:
            tab_name = type_info["name"]
            page = DepartmentPage(
                tab_name=tab_name,
                structure_data=self.structure_data,
                type_key=type_key,
                parent=self
            )
            self.tabWidget.addTab(page, tab_name)




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