# client/windows/system/departments/department_page.py

import os
import sys
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QScrollArea, QMenu, QMessageBox, QApplication,
    QSizePolicy, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.uic import loadUi

from client.windows.animations.collapsible_group import CollapsibleGroup
from client.windows.system.departments.department_card import DepartmentCard
from client.windows.animations.floating_action_button import FloatingActionButton
from client.windows.system.departments.department_dialog import DepartmentDialog
from client.windows.animations.animated_notification import NotificationManager
from client.services.department_service import get_department_service
from client.services.org_service import get_org_service
from client.core.http_client import HttpClient
from client.core.config import config
from client.core.state.app_state import AppState


class DepartmentPage(QWidget):
    """Страница структурных единиц с иерархической группировкой"""

    data_loaded = pyqtSignal()

    def __init__(self, parent=None, http_client: Optional[HttpClient] = None, structure_data=None):
        super().__init__(parent)

        # Используем переданный HttpClient или создаем новый
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

        # Данные
        self.all_items: List[Dict[str, Any]] = []
        self.filtered_items: List[Dict[str, Any]] = []
        self.organizations: List[Dict[str, Any]] = []
        self.departments_flat: List[Dict[str, Any]] = []
        self.employees: List[Dict[str, Any]] = []

        # Если переданы данные структуры, используем их
        self.structure_data = structure_data or []

        # Состояние
        self.current_sort = "А→Я"
        self.is_loading = False
        self._updating = False

        # Инициализация
        self.init_ui()
        self.setup_connections()

        # Создаем менеджер уведомлений
        self.notification_manager = NotificationManager(self, max_visible=3)

        # Загружаем данные
        QTimer.singleShot(100, self.load_data)

    def init_ui(self):
        """Инициализация UI из файла"""
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
        """Возвращает путь к UI файлу"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, '..', '..', '..', 'ui', 'system', 'departments', 'department_page.ui')
        return os.path.normpath(ui_path)

    def setup_connections(self):
        """Настройка сигналов"""
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
        """Загружает данные с сервера"""
        if self.is_loading:
            return

        self.is_loading = True

        try:
            # Загружаем организации
            orgs = self.org_service.get_all_organizations(limit=200)
            self.organizations = orgs if orgs else []
            print(f"[DEBUG] Загружено организаций: {len(self.organizations)}")

            # Если есть структура, загружаем из нее
            if self.structure_data:
                print(f"[DEBUG] Загрузка структуры из переданных данных")
                self.load_from_structure(self.structure_data)
            else:
                # Иначе загружаем тестовые данные
                print(f"[DEBUG] Загрузка тестовых данных")
                self._load_test_data()

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
        """Загружает данные из переданной структуры"""
        self.structure_data = structure_data
        self.all_items = []

        def traverse(node, org_name, org_id, parent_name="", parent_type=""):
            # Если у узла есть дети, обходим их
            if node.get("children"):
                for child in node["children"]:
                    # Определяем тип отдела
                    dept_type = self._detect_department_type(child)
                    type_display = self._get_type_display_name(dept_type)

                    # Если это не корневой узел (не организация), добавляем его как отдел
                    if node.get("id") != org_id:
                        item = {
                            "id": child.get("id"),
                            "name": child.get("name"),
                            "organization_name": org_name,
                            "organization_id": org_id,
                            "parent_name": node.get("name", ""),
                            "department_type": dept_type,
                            "type_display": type_display
                        }
                        self.all_items.append(item)

                    # Рекурсивно обходим детей
                    if child.get("children"):
                        traverse(child, org_name, org_id, child.get("name", ""), dept_type)

        for org in self.structure_data:
            org_name = org.get("name", "Без организации")
            org_id = org.get("id")

            # Добавляем организацию как родительский узел
            if org.get("children"):
                # Определяем тип для корневых детей организации
                for child in org["children"]:
                    dept_type = self._detect_department_type(child)
                    type_display = self._get_type_display_name(dept_type)

                    item = {
                        "id": child.get("id"),
                        "name": child.get("name"),
                        "organization_name": org_name,
                        "organization_id": org_id,
                        "parent_name": org_name,
                        "department_type": dept_type,
                        "type_display": type_display
                    }
                    self.all_items.append(item)

                    # Рекурсивно обходим детей
                    if child.get("children"):
                        traverse(child, org_name, org_id, child.get("name", ""), dept_type)

        print(f"[DEBUG] Загружено {len(self.all_items)} отделов из структуры")

    def _detect_department_type(self, node):
        """Определяет тип отдела по названию или по department_type_id"""
        # Если есть department_type_id, используем его
        if node.get("department_type_id"):
            type_map = {
                1: "divisions",
                2: "departments",
                3: "bureaus",
                4: "sections",
                5: "workshops",
            }
            return type_map.get(node.get("department_type_id"), "departments")

        # Иначе определяем по названию
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
        """Возвращает русское название для типа структуры"""
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
        """Загружает тестовые данные для отделов"""
        self.all_items = [
            {
                "id": 1,
                "name": "Управление информационных технологий",
                "organization_name": "ОАО МАЗ",
                "organization_id": 1,
                "parent_name": "ОАО МАЗ",
                "department_type": "divisions",
                "type_display": "Управления"
            },
            {
                "id": 2,
                "name": "Отдел разработки ПО",
                "organization_name": "ОАО МАЗ",
                "organization_id": 1,
                "parent_name": "Управление информационных технологий",
                "department_type": "departments",
                "type_display": "Отделы"
            },
            {
                "id": 3,
                "name": "Бухгалтерия",
                "organization_name": "ОАО МАЗ",
                "organization_id": 1,
                "parent_name": "ОАО МАЗ",
                "department_type": "departments",
                "type_display": "Отделы"
            }
        ]

    # ==================== СОРТИРОВКА ====================

    def show_sort_menu(self):
        """Показать меню сортировки"""
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

    # ==================== ПОИСК И ФИЛЬТРЫ ====================

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
            if self.has_active_filters():
                self.btnResetFilters.show()
            else:
                self.btnResetFilters.hide()

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
        """Фильтрация и сортировка элементов"""
        filtered = self.all_items.copy()

        if hasattr(self, 'searchEdit'):
            search_text = self.searchEdit.text().strip().lower()
            if search_text:
                filtered = [
                    item for item in filtered
                    if search_text in item.get('name', '').lower() or
                       search_text in item.get('organization_name', '').lower() or
                       search_text in item.get('type_display', '').lower()
                ]

        sort_methods = {
            "А→Я": self.sort_by_name_asc,
            "А→Я (по названию)": self.sort_by_name_asc,
            "Я→А (по названию)": self.sort_by_name_desc,
        }

        sort_func = sort_methods.get(self.current_sort, self.sort_by_name_asc)
        return sort_func(filtered)

    # ==================== ОТОБРАЖЕНИЕ ====================

    def clear_layout(self, layout):
        """Безопасная очистка layout"""
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

    def group_hierarchically(self, items):
        """Группировка по иерархии: Организация → Тип → Отделы"""
        hierarchy = {}

        for item in items:
            org_name = item.get("organization_name", "Без организации")
            type_display = item.get("type_display", "Другие")

            if org_name not in hierarchy:
                hierarchy[org_name] = {}

            if type_display not in hierarchy[org_name]:
                hierarchy[org_name][type_display] = []

            hierarchy[org_name][type_display].append(item)

        return hierarchy

    def update_display(self):
        """Обновление отображения элементов"""
        if self._updating:
            return
        self._updating = True

        try:
            if hasattr(self, 'scrollAreaLayout'):
                self.clear_layout(self.scrollAreaLayout)

            self.filtered_items = self.filter_and_sort_items()

            if not self.filtered_items:
                empty_label = QLabel("Нет данных для отображения")
                empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                empty_label.setStyleSheet("color: #999; font-size: 16px; padding: 40px;")
                if hasattr(self, 'scrollAreaLayout'):
                    self.scrollAreaLayout.addWidget(empty_label)
                    self.scrollAreaLayout.addStretch()
                return

            hierarchy = self.group_hierarchically(self.filtered_items)

            # Сортируем организации: сначала ОАО МАЗ, потом остальные
            org_order = sorted(
                hierarchy.keys(),
                key=lambda x: (0 if x == "ОАО МАЗ" else 1, x)
            )

            for org_name in org_order:
                org_group = CollapsibleGroup(org_name, True)
                org_group.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Minimum
                )
                org_group.setStyleSheet("""
                    QGroupBox {
                        font-size: 16px;
                        font-weight: bold;
                        border: 2px solid #D22730;
                        border-radius: 8px;
                        margin-top: 10px;
                        padding-top: 10px;
                        background-color: #fafafa;
                    }
                    QGroupBox::title {
                        subcontrol-origin: margin;
                        left: 15px;
                        padding: 0 10px 0 10px;
                        color: #D22730;
                    }
                """)

                types = hierarchy[org_name]
                # Сортируем типы по приоритету
                type_order = ["Управления", "Отделы", "Цеха", "Сектора", "Бюро", "Дирекции", "Другие"]
                sorted_types = sorted(
                    types.items(),
                    key=lambda x: type_order.index(x[0]) if x[0] in type_order else len(type_order)
                )

                for type_name, items in sorted_types:
                    type_group = CollapsibleGroup(type_name, True)
                    type_group.setSizePolicy(
                        QSizePolicy.Policy.Expanding,
                        QSizePolicy.Policy.Minimum
                    )
                    type_group.setStyleSheet("""
                        QGroupBox {
                            font-size: 14px;
                            font-weight: bold;
                            border: 1px solid #cccccc;
                            border-radius: 6px;
                            margin-top: 8px;
                            padding-top: 8px;
                            background-color: #f5f5f5;
                        }
                        QGroupBox::title {
                            subcontrol-origin: margin;
                            left: 15px;
                            padding: 0 8px 0 8px;
                            color: #333333;
                        }
                    """)

                    for item in items:
                        card_data = {
                            "id": item.get("id"),
                            "name": item.get("name", ""),
                            "code": str(item.get("id", "")),
                            "leader": item.get("leader", "Не назначен"),
                            "phone": item.get("phone", ""),
                            "description": item.get("parent_name", ""),
                            "type": item.get("type_display", "Не указан"),
                            "organization": item.get("organization_name", "")
                        }

                        item_card = DepartmentCard(card_data)
                        item_card.setMinimumHeight(150)
                        item_card.setMaximumHeight(150)
                        item_card.setSizePolicy(
                            QSizePolicy.Policy.Expanding,
                            QSizePolicy.Policy.Fixed
                        )

                        item_card.edit_clicked.connect(self.on_edit_department)
                        item_card.delete_clicked.connect(self.on_delete_department)

                        type_group.add_widget(item_card)

                    org_group.add_widget(type_group)
                    QTimer.singleShot(50, type_group._delayed_height_update)

                if hasattr(self, 'scrollAreaLayout'):
                    self.scrollAreaLayout.addWidget(org_group)
                QTimer.singleShot(100, org_group._delayed_height_update)

            if hasattr(self, 'scrollAreaLayout'):
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
        """Обработчик нажатия на плавающую кнопку"""
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
        """Создание отдела"""
        try:
            result = self.department_service.create_department(data)

            if result:
                print(f"[DEBUG] Отдел создан: {result}")
                self.show_success_notification(f"Отдел «{result.get('name')}» создан")
                self.load_data()
            else:
                self.show_error_notification("Не удалось создать отдел")

        except Exception as e:
            import logging
            logging.error(f"Ошибка создания отдела: {e}")
            self.show_error_notification("Не удалось создать отдел")

    def on_edit_department(self, data: Dict[str, Any]):
        """Обработчик редактирования отдела"""
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
        """Обновление отдела"""
        try:
            result = self.department_service.update_department(dept_id, data)

            if result:
                print(f"[DEBUG] Отдел обновлен: {result}")
                self.show_success_notification(f"Отдел «{result.get('name')}» обновлен")
                self.load_data()
            else:
                self.show_error_notification("Не удалось обновить отдел")

        except Exception as e:
            import logging
            logging.error(f"Ошибка обновления отдела: {e}")
            self.show_error_notification("Не удалось обновить отдел")

    def on_delete_department(self, dept_id: int):
        """Обработчик удаления отдела"""
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
        """Удаление отдела"""
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


def main():
    """Точка входа для тестирования"""
    app = QApplication(sys.argv)

    window = DepartmentPage()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()