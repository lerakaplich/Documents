import os
import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QScrollArea, QMenu, QMessageBox, QApplication,
    QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi

from client.windows.animations.collapsible_group import CollapsibleGroup
from client.windows.system.departments.department_card import DepartmentCard
from client.windows.animations.floating_action_button import FloatingActionButton


class DepartmentPage(QWidget):
    """Страница структурных единиц с поиском, сортировкой и группировкой по организациям"""

    def __init__(self, tab_name="Структура", structure_data=None, type_key=None, parent=None):
        super().__init__(parent)

        # Данные
        self.tab_name = tab_name
        self.structure_data = structure_data or []
        self.type_key = type_key
        self.all_items = []  # Все элементы этого типа
        self.filtered_items = []

        # Состояние
        self.current_sort = "А→Я"

        # Инициализация
        self.init_ui()
        self.collect_items()
        self.setup_connections()
        self.update_display()

    def init_ui(self):
        """Инициализация UI из файла"""
        ui_path = self.get_ui_path()
        if os.path.exists(ui_path):
            loadUi(ui_path, self)

        # Создаем плавающую кнопку
        self.floating_btn = FloatingActionButton(self)
        self.floating_btn.clicked.connect(self.on_add_department)

        # Подключаемся к скроллу
        self.scrollArea.verticalScrollBar().valueChanged.connect(self.on_scroll)

        # Скрываем кнопку сброса при старте
        self.btnResetFilters.hide()

    def get_ui_path(self):
        """Возвращает путь к UI файлу"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, '..', '..', '..', 'ui', 'system', 'departments', 'department_page.ui')
        return os.path.normpath(ui_path)

    def setup_connections(self):
        """Настройка сигналов"""
        self.btnSort.clicked.connect(self.show_sort_menu)
        self.searchEdit.textChanged.connect(self.on_search_changed)
        self.btnResetFilters.clicked.connect(self.reset_all_filters)

    def collect_items(self):
        """Собирает все элементы нужного типа из структуры"""
        self.all_items = []

        for org in self.structure_data:
            items = self._collect_items_by_type(org, self.type_key)
            for item in items:
                # Добавляем информацию об организации
                item_copy = item.copy()
                item_copy["organization_name"] = org["name"]
                item_copy["organization_id"] = org["id"]
                # Находим родителя
                item_copy["parent_name"] = self._find_parent_name(org, item["id"])
                self.all_items.append(item_copy)

    def _collect_items_by_type(self, node, type_key):
        """Рекурсивно собирает элементы определенного типа из дерева"""
        items = []

        if node.get("children"):
            child_names = [child["name"] for child in node["children"]]
            current_level_type = self._detect_level_type(child_names)

            if current_level_type == type_key:
                items.extend(node["children"])
            else:
                for child in node["children"]:
                    items.extend(self._collect_items_by_type(child, type_key))

        return items

    def _detect_level_type(self, names):
        """Определяет тип уровня по названиям"""
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
        else:
            return "departments"

    def _find_parent_name(self, root_node, target_id):
        """Находит название родительского узла"""

        def search(node, parent_name=""):
            if node["id"] == target_id:
                return parent_name
            for child in node.get("children", []):
                result = search(child, node["name"])
                if result:
                    return result
            return None

        return search(root_node, "")

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

        menu.exec(self.btnSort.mapToGlobal(self.btnSort.rect().bottomLeft()))

    def sort_by_name_asc(self, items):
        """Сортировка по названию А→Я"""
        return sorted(items, key=lambda x: x.get('name', '').lower())

    def sort_by_name_desc(self, items):
        """Сортировка по названию Я→А"""
        return sorted(items, key=lambda x: x.get('name', '').lower(), reverse=True)

    def apply_sort(self, sort_func, sort_name):
        """Применить сортировку"""
        self.current_sort = sort_name
        short_name = sort_name.split('(')[0].strip() if '(' in sort_name else sort_name
        self.btnSort.setText(f"Сортировка ▼ ({short_name})")
        self.update_reset_button_visibility()
        self.update_display()

    def on_search_changed(self):
        """Обработчик изменения текста поиска"""
        self.update_reset_button_visibility()
        self.update_display()

    def has_active_filters(self):
        """Проверяет, есть ли активные фильтры"""
        if self.searchEdit.text().strip():
            return True

        if self.current_sort != "А→Я":
            return True

        return False

    def update_reset_button_visibility(self):
        """Показать или скрыть кнопку сброса"""
        if self.has_active_filters():
            self.btnResetFilters.show()
        else:
            self.btnResetFilters.hide()

    def reset_all_filters(self):
        """Сброс всех фильтров и поиска"""
        self.searchEdit.clear()

        self.current_sort = "А→Я"
        self.btnSort.setText("Сортировка ▼")

        self.btnResetFilters.hide()
        self.update_display()

    def filter_and_sort_items(self):
        """Фильтрация и сортировка элементов"""
        filtered = self.all_items.copy()

        # Поиск
        search_text = self.searchEdit.text().strip().lower()
        if search_text:
            filtered = [
                item for item in filtered
                if search_text in item.get('name', '').lower() or
                   search_text in str(item.get('id', '')).lower()
            ]

        # Сортировка
        sort_methods = {
            "А→Я": self.sort_by_name_asc,
            "А→Я (по названию)": self.sort_by_name_asc,
            "Я→А (по названию)": self.sort_by_name_desc,
        }

        sort_func = sort_methods.get(self.current_sort, self.sort_by_name_asc)
        return sort_func(filtered)

    def group_by_organization(self, items):
        """Группировка элементов по организациям"""
        groups = {}

        for item in items:
            org_name = item.get("organization_name", "Без организации")
            if org_name not in groups:
                groups[org_name] = []
            groups[org_name].append(item)

        return groups

    def update_display(self):
        """Обновление отображения элементов"""
        # Очищаем layout
        for i in reversed(range(self.scrollAreaLayout.count())):
            widget = self.scrollAreaLayout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # Получаем отфильтрованные и отсортированные элементы
        self.filtered_items = self.filter_and_sort_items()
        groups = self.group_by_organization(self.filtered_items)

        # Сортируем организации: МАЗ первый
        org_order = sorted(groups.keys(), key=lambda x: (x != "ОАО МАЗ", x))

        for i, org_name in enumerate(org_order):
            items = groups[org_name]
            if not items:
                continue

            # Первая группа развернута
            is_expanded = (i == 0)
            group = CollapsibleGroup(org_name, is_expanded)

            for item in items:
                card_data = {
                    "name": item["name"],
                    "code": str(item["id"]),
                    "leader": "Не назначен",
                    "phone": f"{item['id']}00",
                    "description": f"{item['name']} организации {org_name}"
                }

                item_card = DepartmentCard(card_data)
                group.add_widget(item_card)

            self.scrollAreaLayout.addWidget(group)

        self.scrollAreaLayout.addStretch()

        # Обновляем позицию плавающей кнопки
        self.position_floating_button()

    def position_floating_button(self):
        """Позиционирование плавающей кнопки в правом нижнем углу"""
        if hasattr(self, 'floating_btn'):
            margin = 20
            x = self.width() - self.floating_btn.width() - margin
            y = self.height() - self.floating_btn.height() - margin
            self.floating_btn.update_base_position(x, y)
            self.floating_btn.raise_()

    def on_scroll(self, value):
        """Обработчик скролла"""
        if hasattr(self, 'floating_btn'):
            self.floating_btn.hide_with_animation()
            self.floating_btn.start_hide_timer()

    def resizeEvent(self, event):
        """Обработчик изменения размера для позиционирования кнопки"""
        super().resizeEvent(event)
        self.position_floating_button()

    def on_add_department(self):
        """Обработчик нажатия на плавающую кнопку добавления"""
        QMessageBox.information(
            self,
            "Добавление",
            f"Добавление нового элемента в «{self.tab_name}»\n\nЭта функция в разработке."
        )

    def on_edit_department(self, data):
        """Обработчик редактирования"""
        print(f"Редактирование: {data.get('name')}")

    def on_delete_department(self, item_id):
        """Обработчик удаления"""
        print(f"Удаление ID: {item_id}")


# Для тестирования
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Тестовые данные
    test_structure = [
        {
            "id": 1,
            "name": "ОАО МАЗ",
            "children": [
                {"id": 2, "name": "Дирекция", "children": []},
                {
                    "id": 3,
                    "name": "Техническая дирекция",
                    "children": [
                        {"id": 4, "name": "Конструкторский отдел", "children": []},
                        {"id": 5, "name": "Технологический отдел", "children": []},
                    ]
                },
            ]
        }
    ]

    window = QWidget()
    window.setWindowTitle("Тест - Структурные единицы")
    window.setGeometry(100, 100, 1000, 700)

    # type_key="departments" покажет все отделы
    dept_page = DepartmentPage(
        tab_name="Отделы",
        structure_data=test_structure,
        type_key="departments"
    )

    layout = QVBoxLayout(window)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(dept_page)

    window.show()
    sys.exit(app.exec())