# client/windows/system/departments/department_page.py

import os
import sys
import json
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QScrollArea, QMenu, QMessageBox, QApplication,
    QSizePolicy, QLabel, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon
from PyQt6.uic import loadUi

from client.windows.animations.floating_action_button import FloatingActionButton
from client.windows.system.departments.department_dialog import DepartmentDialog
from client.windows.animations.animated_notification import NotificationManager
from client.services.department_service import get_department_service
from client.services.org_service import get_org_service
from client.core.http_client import HttpClient
from client.core.config import config
from client.core.state.app_state import AppState

from client.windows.system.departments.department_node import DepartmentNode
from client.windows.system.employees.employee_card import EmployeeCard


class DepartmentPage(QWidget):
    """
    Страница структурных единиц с иерархическим отображением в виде дерева.
    Каждый узел (отдел) можно раскрыть, чтобы увидеть его карточку, дочерние отделы и сотрудников.
    """

    data_loaded = pyqtSignal()

    def __init__(self, parent=None, http_client: Optional[HttpClient] = None, structure_data=None):
        super().__init__(parent)

        if http_client is None:
            app_state = AppState()
            if app_state.http_client:
                self.http_client = app_state.http_client
            else:
                self.http_client = HttpClient(config.base_url)
        else:
            self.http_client = http_client

        self.department_service = get_department_service(self.http_client)
        self.org_service = get_org_service(self.http_client)

        self.all_items: List[Dict[str, Any]] = []
        self.filtered_items: List[Dict[str, Any]] = []
        self.organizations: List[Dict[str, Any]] = []
        self.employees: List[Dict[str, Any]] = []
        self.employees_by_id: Dict[int, Dict[str, Any]] = {}

        self.structure_data = structure_data or []

        self.current_sort = "А→Я"
        self.is_loading = False
        self._updating = False

        self.init_ui()
        self.setup_connections()

        self.notification_manager = NotificationManager(self, max_visible=3)

        QTimer.singleShot(100, self.load_data)

    def init_ui(self):
        ui_path = self.get_ui_path()
        if os.path.exists(ui_path):
            loadUi(ui_path, self)

        if hasattr(self, 'scrollArea'):
            self.scrollArea.setWidgetResizable(True)
            self.scrollArea.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Expanding
            )
            if hasattr(self, 'scrollAreaWidgetContents'):
                self.scrollAreaWidgetContents.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Minimum
                )

        self.floating_btn = FloatingActionButton(self)
        self.floating_btn.clicked.connect(self.on_add_department)

        if hasattr(self, 'scrollArea') and hasattr(self.scrollArea, 'verticalScrollBar'):
            self.scrollArea.verticalScrollBar().valueChanged.connect(self.on_scroll)

        if hasattr(self, 'btnResetFilters'):
            self.btnResetFilters.hide()

    def get_ui_path(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, '..', '..', '..', 'ui', 'system', 'departments', 'department_page.ui')
        return os.path.normpath(ui_path)

    def setup_connections(self):
        if hasattr(self, 'btnSort'):
            self.btnSort.clicked.connect(self.show_sort_menu)
        if hasattr(self, 'searchEdit'):
            self.searchEdit.textChanged.connect(self.on_search_changed)
        if hasattr(self, 'btnResetFilters'):
            self.btnResetFilters.clicked.connect(self.reset_all_filters)

    def show_success_notification(self, message: str):
        self.notification_manager.show_notification(f"✅ {message}", duration=2500)

    def show_error_notification(self, message: str):
        self.notification_manager.show_notification(f"❌ {message}", duration=3000)

    def show_info_notification(self, message: str):
        self.notification_manager.show_notification(f"ℹ️ {message}", duration=2500)

    # ==================== ЗАГРУЗКА ДАННЫХ ====================

    def load_data(self):
        if self.is_loading:
            return
        self.is_loading = True

        try:
            orgs = self.org_service.get_all_organizations(limit=200)
            self.organizations = orgs if orgs else []
            print(f"[DEBUG] Загружено организаций: {len(self.organizations)}")

            if self.structure_data:
                print(f"[DEBUG] Загрузка структуры из переданных данных")
                self.load_from_structure(self.structure_data)
            else:
                print(f"[DEBUG] Загрузка тестовых данных")
                self._load_test_data()

            if not self.employees_by_id:
                self._attach_test_employees_to_structure()
                self._collect_employees_from_structure(self.structure_data)

            self._collect_employees_from_structure(self.structure_data)
            print(f"[DEBUG] Всего сотрудников в словаре: {len(self.employees_by_id)}")

            print("[DEBUG] Структура после загрузки (первые 2 уровня):")
            for org in self.structure_data[:1]:
                print(f"  Организация: {org.get('name')}")
                for child in org.get('children', [])[:2]:
                    emp_count = len(child.get('employees', []))
                    print(f"    Отдел: {child.get('name')} | сотрудников: {emp_count}")

            self.is_loading = False
            self.update_display()
            self.data_loaded.emit()

            if self.all_items:
                self.show_success_notification(f"Загружено {len(self.all_items)} отделов")

        except Exception as e:
            self.is_loading = False
            import logging
            import traceback
            logging.error(f"Ошибка загрузки данных: {e}")
            traceback.print_exc()
            self.show_error_notification("Не удалось загрузить данные")

    def load_from_structure(self, structure_data):
        self.structure_data = structure_data
        self.all_items = []

        def traverse(node, org_name, org_id, parent_name="", parent_type=""):
            for child in node.get("children", []):
                dept_type = self._detect_department_type(child)
                type_display = self._get_type_display_name(dept_type)

                if node.get("id") != org_id:
                    item = {
                        "id": child.get("id"),
                        "name": child.get("name"),
                        "organization_name": org_name,
                        "organization_id": org_id,
                        "parent_name": parent_name,
                        "department_type": dept_type,
                        "type_display": type_display,
                        "leader": child.get("leader", ""),
                        "phone": child.get("phone", ""),
                        "description": child.get("description", ""),
                    }
                    self.all_items.append(item)

                if child.get("children"):
                    traverse(child, org_name, org_id, child.get("name", ""), dept_type)

        for org in self.structure_data:
            org_name = org.get("name", "Без организации")
            org_id = org.get("id")
            for child in org.get("children", []):
                dept_type = self._detect_department_type(child)
                type_display = self._get_type_display_name(dept_type)
                item = {
                    "id": child.get("id"),
                    "name": child.get("name"),
                    "organization_name": org_name,
                    "organization_id": org_id,
                    "parent_name": org_name,
                    "department_type": dept_type,
                    "type_display": type_display,
                    "leader": child.get("leader", ""),
                    "phone": child.get("phone", ""),
                    "description": child.get("description", ""),
                }
                self.all_items.append(item)
                if child.get("children"):
                    traverse(child, org_name, org_id, child.get("name", ""), dept_type)

        print(f"[DEBUG] Загружено {len(self.all_items)} отделов из структуры")

    def _collect_employees_from_structure(self, structure):
        def traverse(nodes):
            for node in nodes:
                if "employees" in node and isinstance(node["employees"], list):
                    for emp in node["employees"]:
                        if isinstance(emp, dict) and "id" in emp:
                            self.employees_by_id[emp["id"]] = emp
                            print(f"[DEBUG] Добавлен сотрудник: {emp.get('last_name')} (ID: {emp['id']})")
                if "employees_ids" in node and isinstance(node["employees_ids"], list):
                    for emp_id in node["employees_ids"]:
                        if emp_id not in self.employees_by_id:
                            emp = next((e for e in self.employees if e.get("id") == emp_id), None)
                            if emp:
                                self.employees_by_id[emp_id] = emp
                                print(f"[DEBUG] Найден сотрудник по ID {emp_id}: {emp.get('last_name')}")
                if "employee_ids" in node and isinstance(node["employee_ids"], list):
                    for emp_id in node["employee_ids"]:
                        if emp_id not in self.employees_by_id:
                            emp = next((e for e in self.employees if e.get("id") == emp_id), None)
                            if emp:
                                self.employees_by_id[emp_id] = emp
                                print(f"[DEBUG] Найден сотрудник по ID {emp_id}: {emp.get('last_name')}")
                if "children" in node:
                    traverse(node["children"])
        traverse(structure)

    # ==================== ОПРЕДЕЛЕНИЕ ТИПОВ ====================

    def _detect_department_type(self, node):
        if node.get("department_type_id"):
            type_map = {
                1: "divisions",
                2: "departments",
                3: "bureaus",
                4: "sections",
                5: "workshops",
            }
            return type_map.get(node.get("department_type_id"), "departments")

        name = node.get("name", "").lower()
        if "управл" in name:
            return "divisions"
        elif "цех" in name:
            return "workshops"
        elif "бюро" in name:
            return "bureaus"
        elif "сектор" in name:
            return "sections"
        elif "дирекц" in name:
            return "directorates"
        elif "отдел" in name:
            return "departments"
        else:
            return "departments"

    def _get_type_display_name(self, type_key):
        names = {
            "divisions": "Управления",
            "departments": "Отделы",
            "workshops": "Цеха",
            "branches": "Филиалы",
            "sections": "Сектора",
            "bureaus": "Бюро",
            "directorates": "Дирекции",
        }
        return names.get(type_key, type_key.capitalize())

    def _load_test_data(self):
        employees_data = {
            101: {
                "id": 101,
                "last_name": "Иванов",
                "first_name": "Иван",
                "patronymic": "Иванович",
                "position_name": "Начальник управления",
                "work_phone": "101",
                "email": "i.ivanov@maz.by"
            },
            102: {
                "id": 102,
                "last_name": "Петрова",
                "first_name": "Мария",
                "patronymic": "Сергеевна",
                "position_name": "Инженер-программист",
                "work_phone": "102",
                "email": "m.petrova@maz.by"
            },
            103: {
                "id": 103,
                "last_name": "Сидоров",
                "first_name": "Алексей",
                "patronymic": "Петрович",
                "position_name": "Системный администратор",
                "work_phone": "103",
                "email": "a.sidorov@maz.by"
            },
            104: {
                "id": 104,
                "last_name": "Козлова",
                "first_name": "Елена",
                "patronymic": "Викторовна",
                "position_name": "Специалист по документообороту",
                "work_phone": "104",
                "email": "e.kozlova@maz.by"
            },
            105: {
                "id": 105,
                "last_name": "Морозов",
                "first_name": "Дмитрий",
                "patronymic": "Андреевич",
                "position_name": "Конструктор",
                "work_phone": "105",
                "email": "d.morozov@maz.by"
            },
            106: {
                "id": 106,
                "last_name": "Новикова",
                "first_name": "Ольга",
                "patronymic": "Игоревна",
                "position_name": "Экономист",
                "work_phone": "106",
                "email": "o.novikova@maz.by"
            },
            107: {
                "id": 107,
                "last_name": "Васильев",
                "first_name": "Сергей",
                "patronymic": "Николаевич",
                "position_name": "Руководитель проекта",
                "work_phone": "107",
                "email": "s.vasiliev@maz.by"
            },
            108: {
                "id": 108,
                "last_name": "Павлова",
                "first_name": "Татьяна",
                "patronymic": "Алексеевна",
                "position_name": "Бухгалтер",
                "work_phone": "108",
                "email": "t.pavlova@maz.by"
            },
        }

        self.employees = list(employees_data.values())
        self.employees_by_id = employees_data.copy()

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
                                "department_type_id": 1,
                                "leader": "Иванов И.И.",
                                "phone": "+375 17 123-45-67",
                                "description": "Управление ИТ",
                                "employees": [
                                    employees_data[101],
                                    employees_data[102],
                                    employees_data[103]
                                ],
                                "children": [
                                    {
                                        "id": 4,
                                        "name": "Отдел разработки СЭД",
                                        "department_type_id": 2,
                                        "leader": "Петров П.П.",
                                        "phone": "+375 29 987-65-43",
                                        "description": "Разработка СЭД",
                                        "employees": [employees_data[104]],
                                        "children": []
                                    },
                                    {
                                        "id": 5,
                                        "name": "Отдел системного администрирования",
                                        "department_type_id": 2,
                                        "leader": "Сидоров С.С.",
                                        "phone": "+375 29 111-22-33",
                                        "description": "Администрирование систем",
                                        "employees": [employees_data[105], employees_data[106]],
                                        "children": []
                                    }
                                ]
                            },
                            {
                                "id": 6,
                                "name": "Канцелярия (Общий отдел)",
                                "department_type_id": 2,
                                "leader": "Козлова Е.В.",
                                "phone": "+375 17 234-56-78",
                                "description": "Общий отдел",
                                "employees": [employees_data[107], employees_data[108]],
                                "children": []
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
                                "department_type_id": 2,
                                "leader": "Смирнов А.А.",
                                "phone": "+375 29 333-44-55",
                                "description": "Конструирование",
                                "employees": [],
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
                        "employees": [],
                        "children": []
                    }
                ]
            }
        ]

        self.load_from_structure(self.structure_data)

    # ==================== СОРТИРОВКА И ПОИСК ====================

    def show_sort_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { 
                background-color: white; 
                border: 1px solid #c0c0c0; 
                border-radius: 5px; 
                padding: 5px; 
                color: black;
            }
            QMenu::item { 
                padding: 8px 25px 8px 15px; 
                border-radius: 3px; 
                font-size: 14px; 
            }
            QMenu::item:selected { 
                background-color: #e3f2fd; 
            }
            QMenu::separator { 
                height: 1px; 
                background: #e0e0e0; 
                margin: 5px 10px; 
            }
        """)
        sort_options = {
            "А→Я (по названию)": self.sort_by_name_asc,
            "Я→А (по названию)": self.sort_by_name_desc,
        }
        for name, func in sort_options.items():
            action = menu.addAction(name)
            action.triggered.connect(lambda checked, f=func, n=name: self.apply_sort(f, n))
        if hasattr(self, 'btnSort'):
            menu.exec(self.btnSort.mapToGlobal(self.btnSort.rect().bottomLeft()))

    def sort_by_name_asc(self, items):
        return sorted(items, key=lambda x: x.get('name', '').lower())

    def sort_by_name_desc(self, items):
        return sorted(items, key=lambda x: x.get('name', '').lower(), reverse=True)

    def apply_sort(self, sort_func, sort_name):
        self.current_sort = sort_name
        short_name = sort_name.split('(')[0].strip() if '(' in sort_name else sort_name
        if hasattr(self, 'btnSort'):
            self.btnSort.setText(f"Сортировка ▼ ({short_name})")
        self.update_reset_button_visibility()
        self.update_display()

    def on_search_changed(self):
        self.update_reset_button_visibility()
        self.update_display()

    def has_active_filters(self):
        if hasattr(self, 'searchEdit') and self.searchEdit.text().strip():
            return True
        if self.current_sort != "А→Я":
            return True
        return False

    def update_reset_button_visibility(self):
        if hasattr(self, 'btnResetFilters'):
            self.btnResetFilters.setVisible(self.has_active_filters())

    def reset_all_filters(self):
        if hasattr(self, 'searchEdit'):
            self.searchEdit.clear()
        self.current_sort = "А→Я"
        if hasattr(self, 'btnSort'):
            self.btnSort.setText("Сортировка ▼")
        if hasattr(self, 'btnResetFilters'):
            self.btnResetFilters.hide()
        self.update_display()

    def filter_and_sort_items(self):
        filtered = self.all_items.copy()
        if hasattr(self, 'searchEdit'):
            search_text = self.searchEdit.text().strip().lower()
            if search_text:
                filtered = [
                    item for item in filtered
                    if search_text in item.get('name', '').lower()
                    or search_text in item.get('organization_name', '').lower()
                    or search_text in item.get('type_display', '').lower()
                ]
        sort_methods = {
            "А→Я": self.sort_by_name_asc,
            "А→Я (по названию)": self.sort_by_name_asc,
            "Я→А (по названию)": self.sort_by_name_desc,
        }
        sort_func = sort_methods.get(self.current_sort, self.sort_by_name_asc)
        return sort_func(filtered)

    # ==================== ПОСТРОЕНИЕ ДЕРЕВА ====================

    def build_tree_from_structure(self, structure_data):
        root_nodes = []
        for org in structure_data:
            org_node = DepartmentNode(
                {
                    'id': org.get('id'),
                    'name': org.get('name'),
                    'type_display': 'Организация',
                    'code': org.get('code', '')
                },
                is_root=True
            )
            for child in org.get('children', []):
                self._add_child_nodes(org_node, child, org.get('name'))
            root_nodes.append(org_node)
        return root_nodes

    def _add_child_nodes(self, parent_node, node_data, org_name):
        dept_type = self._detect_department_type(node_data)
        type_display = self._get_type_display_name(dept_type)

        item_data = {
            'id': node_data.get('id'),
            'name': node_data.get('name'),
            'type_display': type_display,
            'code': str(node_data.get('id', '')),
            'leader': node_data.get('leader', 'Не назначен'),
            'phone': node_data.get('phone', ''),
            'description': node_data.get('description', ''),
            'organization': org_name,
        }

        node = DepartmentNode(item_data)

        card_data = {
            'id': item_data['id'],
            'name': item_data['name'],
            'code': item_data['code'],
            'leader': item_data['leader'],
            'phone': item_data['phone'],
            'description': item_data['description'],
            'type': item_data['type_display'],
            'organization': item_data['organization']
        }
        node.set_card_data(card_data)

        # --- ПОЛУЧАЕМ СПИСОК СОТРУДНИКОВ ---
        employees_list = []
        if "employees" in node_data and isinstance(node_data["employees"], list):
            employees_list = node_data["employees"]
        elif "employees_ids" in node_data and isinstance(node_data["employees_ids"], list):
            for emp_id in node_data["employees_ids"]:
                if emp_id in self.employees_by_id:
                    employees_list.append(self.employees_by_id[emp_id])
        elif "employee_ids" in node_data and isinstance(node_data["employee_ids"], list):
            for emp_id in node_data["employee_ids"]:
                if emp_id in self.employees_by_id:
                    employees_list.append(self.employees_by_id[emp_id])

        # --- ГРУППИРОВКА В "СОТРУДНИКИ" С ИКОНКАМИ ---
        if employees_list:
            group = self._create_employee_group(
                f"Сотрудники ({len(employees_list)})",
                is_expanded=True
            )
            for emp in employees_list:
                if isinstance(emp, dict) and "id" in emp:
                    employee_card = self._create_employee_card(emp)
                    group.add_card(employee_card)
            node.add_content_widget(group)

        # --- ПРОБРАСЫВАЕМ СИГНАЛЫ ---
        node.edit_clicked.connect(self.on_edit_department)
        node.delete_clicked.connect(self.on_delete_department)

        # --- РЕКУРСИЯ ДЛЯ ДОЧЕРНИХ ОТДЕЛОВ ---
        for child in node_data.get('children', []):
            self._add_child_nodes(node, child, org_name)

        node.update_content_geometry()
        parent_node.add_child(node)

    def _create_employee_group(self, title: str, is_expanded: bool = True):
        """
        Создаёт группу для сотрудников с иконками-стрелками, как в DepartmentNode.
        Возвращает виджет с методом add_card.
        """
        # Загружаем иконки (как в DepartmentNode)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        icons_dir = os.path.join(base_dir, 'icons')
        down_path = os.path.join(icons_dir, 'down_arrow.svg')
        up_path = os.path.join(icons_dir, 'up_arrow.svg')
        down_icon = QIcon(down_path) if os.path.exists(down_path) else QIcon()
        up_icon = QIcon(up_path) if os.path.exists(up_path) else QIcon()

        # Виджет-контейнер
        group_widget = QWidget()
        group_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Заголовок (как у DepartmentNode) — убираем фон, оставляем только рамку
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #DEE2E6;
                border-radius: 6px;
                padding: 4px 8px;
            }
            QFrame:hover {
                background-color: #FDFBF7;
                border: 1px solid #CCAB6E;
                border-radius: 6px;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(8, 4, 8, 4)

        # Кнопка-стрелка
        expand_btn = QPushButton()
        expand_btn.setFixedSize(24, 24)
        expand_btn.setFlat(True)
        expand_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        expand_btn.setStyleSheet("QPushButton { border: none; background: transparent; }")
        expand_btn.setIcon(down_icon if not is_expanded else up_icon)
        expand_btn.setIconSize(QSize(16, 16))

        # Заголовок
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #212529; background: transparent; border: none;")

        header_layout.addWidget(expand_btn)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # Контейнер для карточек
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 4, 0, 8)
        content_layout.setSpacing(8)

        # Основной layout
        main_layout = QVBoxLayout(group_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)
        main_layout.addWidget(header_frame)
        main_layout.addWidget(content_widget)

        # Анимация
        animation = QPropertyAnimation(content_widget, b"maximumHeight")
        animation.setDuration(250)
        animation.setEasingCurve(QEasingCurve.Type.InOutCubic)

        expanded = is_expanded

        def toggle():
            nonlocal expanded
            expanded = not expanded
            expand_btn.setIcon(up_icon if expanded else down_icon)
            animation.stop()
            if expanded:
                content_widget.setVisible(True)
                content_widget.updateGeometry()
                content_widget.adjustSize()
                target = content_widget.sizeHint().height()
                if target <= 0:
                    target = 100
                content_widget.setMaximumHeight(0)
                animation.setStartValue(0)
                animation.setEndValue(target)
            else:
                current = content_widget.height()
                if current <= 0:
                    current = 100
                animation.setStartValue(current)
                animation.setEndValue(0)
            animation.start()

        def on_animation_finished():
            if not expanded:
                content_widget.setVisible(False)
                content_widget.setMaximumHeight(0)
            else:
                content_widget.setMaximumHeight(16777215)

        animation.finished.connect(on_animation_finished)

        # Клик по заголовку или кнопке
        header_frame.mousePressEvent = lambda event: toggle()
        expand_btn.clicked.connect(toggle)

        # Начальное состояние
        if expanded:
            content_widget.setVisible(True)
            content_widget.setMaximumHeight(16777215)
        else:
            content_widget.setVisible(False)
            content_widget.setMaximumHeight(0)

        # Метод для добавления карточек
        group_widget.add_card = lambda widget: content_layout.addWidget(widget)

        return group_widget

    def _create_employee_card(self, emp_data):
        full_name = f"{emp_data.get('last_name', '')} {emp_data.get('first_name', '')} {emp_data.get('patronymic', '')}".strip()
        if not full_name:
            full_name = f"Сотрудник #{emp_data.get('id', '?')}"

        card_data = {
            "id": emp_data.get('id'),
            "display_number": "",
            "full_name": full_name,
            "position": emp_data.get('position_name', 'Должность не указана'),
            "company": "",
            "department": "",
            "subdivision": "",
            "work_phone": emp_data.get('work_phone', ''),
            "email": emp_data.get('email', ''),
            "rights": "Сотрудник"
        }
        card = EmployeeCard(card_data)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        print(f"[DEBUG] Создана карточка для {full_name}")
        return card

    # ==================== ОТОБРАЖЕНИЕ ====================

    def clear_layout(self, layout):
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()
            elif item.spacerItem():
                continue
            elif item.layout():
                self.clear_layout(item.layout())

    def update_display(self):
        if self._updating:
            return
        self._updating = True

        try:
            if hasattr(self, 'scrollAreaLayout'):
                self.clear_layout(self.scrollAreaLayout)

            if not self.structure_data:
                empty_label = QLabel("Нет данных для отображения")
                empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                empty_label.setStyleSheet("color: #999; font-size: 16px; padding: 40px;")
                self.scrollAreaLayout.addWidget(empty_label)
                self.scrollAreaLayout.addStretch()
                return

            search_text = ""
            if hasattr(self, 'searchEdit'):
                search_text = self.searchEdit.text().strip().lower()

            def filter_node(node_data):
                if not search_text:
                    return True
                name = node_data.get('name', '').lower()
                if search_text in name:
                    return True
                for child in node_data.get('children', []):
                    if filter_node(child):
                        return True
                return False

            filtered_structure = []
            for org in self.structure_data:
                org_name = org.get('name', '').lower()
                if search_text and search_text not in org_name:
                    filtered_children = []
                    for child in org.get('children', []):
                        if filter_node(child):
                            filtered_children.append(child)
                    if filtered_children:
                        org_copy = org.copy()
                        org_copy['children'] = filtered_children
                        filtered_structure.append(org_copy)
                else:
                    filtered_structure.append(org)

            if not filtered_structure:
                empty_label = QLabel("Нет данных, соответствующих поиску")
                empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                empty_label.setStyleSheet("color: #999; font-size: 16px; padding: 40px;")
                self.scrollAreaLayout.addWidget(empty_label)
                self.scrollAreaLayout.addStretch()
                return

            root_nodes = self.build_tree_from_structure(filtered_structure)

            for node in root_nodes:
                self.scrollAreaLayout.addWidget(node)
            self.scrollAreaLayout.addStretch()

            if hasattr(self, 'scrollArea') and hasattr(self.scrollArea, 'verticalScrollBar'):
                self.scrollArea.verticalScrollBar().setValue(0)

        finally:
            self._updating = False
            if hasattr(self, 'scrollAreaWidgetContents'):
                self.scrollAreaWidgetContents.updateGeometry()
            if hasattr(self, 'scrollArea'):
                self.scrollArea.updateGeometry()
            self.updateGeometry()

    # ==================== CRUD ОПЕРАЦИИ ====================

    def on_add_department(self):
        dialog = DepartmentDialog(
            self,
            organizations=self.organizations,
            departments=self.all_items,
            employees=self.employees
        )
        if dialog.exec():
            data = dialog.get_data()
            if data:
                self._create_department(data)

    def _create_department(self, data: Dict[str, Any]):
        try:
            result = self.department_service.create_department(data)
            if result:
                self.show_success_notification(f"Отдел «{result.get('name')}» создан")
                self.load_data()
            else:
                self.show_error_notification("Не удалось создать отдел")
        except Exception as e:
            import logging
            logging.error(f"Ошибка создания отдела: {e}")
            self.show_error_notification("Не удалось создать отдел")

    def on_edit_department(self, data: Dict[str, Any]):
        dept_id = data.get('id')
        if not dept_id:
            self.show_error_notification("ID отдела не найден")
            return
        try:
            server_dept = self.department_service.get_department(dept_id)
            if not server_dept:
                server_dept = data
            dialog = DepartmentDialog(
                self,
                department_data=server_dept,
                organizations=self.organizations,
                departments=self.all_items,
                employees=self.employees
            )
            if dialog.exec():
                updated_data = dialog.get_data()
                self._update_department(dept_id, updated_data)
        except Exception as e:
            import logging
            logging.error(f"Ошибка редактирования отдела: {e}")
            self.show_error_notification("Не удалось загрузить данные отдела")

    def _update_department(self, dept_id: int, data: Dict[str, Any]):
        try:
            result = self.department_service.update_department(dept_id, data)
            if result:
                self.show_success_notification(f"Отдел «{result.get('name')}» обновлен")
                self.load_data()
            else:
                self.show_error_notification("Не удалось обновить отдел")
        except Exception as e:
            import logging
            logging.error(f"Ошибка обновления отдела: {e}")
            self.show_error_notification("Не удалось обновить отдел")

    def on_delete_department(self, dept_id: int):
        dept_name = "Неизвестный отдел"
        for item in self.all_items:
            if item.get('id') == dept_id:
                dept_name = item.get('name', dept_name)
                break
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить отдел '{dept_name}'?\n\nЭто действие нельзя отменить.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._delete_department(dept_id, dept_name)

    def _delete_department(self, dept_id: int, dept_name: str):
        try:
            success = self.department_service.delete_department(dept_id)
            if success:
                self.show_success_notification(f"Отдел «{dept_name}» удален")
                self.load_data()
            else:
                self.show_error_notification("Не удалось удалить отдел")
        except Exception as e:
            import logging
            logging.error(f"Ошибка удаления отдела: {e}")
            self.show_error_notification("Не удалось удалить отдел")

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================

    def position_floating_button(self):
        if hasattr(self, 'floating_btn'):
            margin = 20
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
        if hasattr(self, 'notification_manager'):
            self.notification_manager.container.setGeometry(
                0, 0, self.width(), self.height()
            )

    def _attach_test_employees_to_structure(self):
        employees_data = {
            101: {
                "id": 101,
                "last_name": "Иванов",
                "first_name": "Иван",
                "patronymic": "Иванович",
                "position_name": "Начальник управления",
                "work_phone": "101",
                "email": "i.ivanov@maz.by"
            },
            102: {
                "id": 102,
                "last_name": "Петрова",
                "first_name": "Мария",
                "patronymic": "Сергеевна",
                "position_name": "Инженер-программист",
                "work_phone": "102",
                "email": "m.petrova@maz.by"
            },
            103: {
                "id": 103,
                "last_name": "Сидоров",
                "first_name": "Алексей",
                "patronymic": "Петрович",
                "position_name": "Системный администратор",
                "work_phone": "103",
                "email": "a.sidorov@maz.by"
            },
            104: {
                "id": 104,
                "last_name": "Козлова",
                "first_name": "Елена",
                "patronymic": "Викторовна",
                "position_name": "Специалист по документообороту",
                "work_phone": "104",
                "email": "e.kozlova@maz.by"
            },
            105: {
                "id": 105,
                "last_name": "Морозов",
                "first_name": "Дмитрий",
                "patronymic": "Андреевич",
                "position_name": "Конструктор",
                "work_phone": "105",
                "email": "d.morozov@maz.by"
            },
            106: {
                "id": 106,
                "last_name": "Новикова",
                "first_name": "Ольга",
                "patronymic": "Игоревна",
                "position_name": "Экономист",
                "work_phone": "106",
                "email": "o.novikova@maz.by"
            },
            107: {
                "id": 107,
                "last_name": "Васильев",
                "first_name": "Сергей",
                "patronymic": "Николаевич",
                "position_name": "Руководитель проекта",
                "work_phone": "107",
                "email": "s.vasiliev@maz.by"
            },
            108: {
                "id": 108,
                "last_name": "Павлова",
                "first_name": "Татьяна",
                "patronymic": "Алексеевна",
                "position_name": "Бухгалтер",
                "work_phone": "108",
                "email": "t.pavlova@maz.by"
            },
        }

        self.employees_by_id.update(employees_data)
        self.employees = list(employees_data.values())

        def attach_to_node(node):
            dept_id = node.get('id')
            if dept_id == 3:
                node['employees'] = [employees_data[101], employees_data[102], employees_data[103]]
            elif dept_id == 4:
                node['employees'] = [employees_data[104]]
            elif dept_id == 5:
                node['employees'] = [employees_data[105], employees_data[106]]
            elif dept_id == 6:
                node['employees'] = [employees_data[107], employees_data[108]]
            else:
                if 'employees' not in node:
                    node['employees'] = []
            for child in node.get('children', []):
                attach_to_node(child)

        for org in self.structure_data:
            for child in org.get('children', []):
                attach_to_node(child)

        print("[DEBUG] Тестовые сотрудники добавлены в структуру")


def main():
    app = QApplication(sys.argv)
    window = DepartmentPage()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()