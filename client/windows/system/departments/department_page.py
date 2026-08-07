import os
import sys

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLineEdit, QScrollArea, QMenu, QMessageBox, QApplication,
    QSizePolicy, QLabel
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.uic import loadUi

from client.windows.animations.collapsible_group import CollapsibleGroup
from client.windows.system.departments.department_card import DepartmentCard
from client.windows.animations.floating_action_button import FloatingActionButton
from client.windows.system.departments.department_dialog import DepartmentDialog


class DepartmentPage(QWidget):
    """Страница структурных единиц с иерархической группировкой: Организация → Тип → Отделы"""

    def __init__(self, tab_name="Структура", structure_data=None, parent=None):
        super().__init__(parent)

        # Данные
        self.tab_name = tab_name
        self.structure_data = structure_data or []
        self.all_items = []  # Все элементы
        self.filtered_items = []

        # Состояние
        self.current_sort = "А→Я"

        # Инициализация
        self.init_ui()
        self.collect_all_departments()
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

    def collect_all_departments(self):
        """Собирает все отделы (всех типов) из структуры"""
        self.all_items = []

        def traverse(node, org_name, org_id, parent_name=""):
            # Если у узла есть дети, проверяем их названия для определения типа
            if node.get("children"):
                # Проверяем, является ли текущий узел родителем для отделов
                child_names = [child["name"] for child in node["children"]]
                level_type = self._detect_level_type(child_names)

                # Если это уровень отделов, добавляем детей
                if level_type:
                    for child in node["children"]:
                        item = {
                            "id": child["id"],
                            "name": child["name"],
                            "organization_name": org_name,
                            "organization_id": org_id,
                            "parent_name": node["name"],
                            "department_type": level_type,
                            "type_display": self._get_type_display_name(level_type)
                        }
                        self.all_items.append(item)

                # Рекурсивно обходим детей
                for child in node["children"]:
                    traverse(child, org_name, org_id, node["name"])

        for org in self.structure_data:
            traverse(org, org["name"], org["id"])

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
                   search_text in str(item.get('id', '')).lower() or
                   search_text in item.get('organization_name', '').lower()
            ]

        # Сортировка
        sort_methods = {
            "А→Я": self.sort_by_name_asc,
            "А→Я (по названию)": self.sort_by_name_asc,
            "Я→А (по названию)": self.sort_by_name_desc,
        }

        sort_func = sort_methods.get(self.current_sort, self.sort_by_name_asc)
        return sort_func(filtered)

    def group_hierarchically(self, items):
        """
        Группировка элементов по иерархии:
        Организация → Тип подразделения → Отделы
        """
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
        # Очищаем layout
        while self.scrollAreaLayout.count():
            item = self.scrollAreaLayout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.spacerItem():
                del item

        # Получаем отфильтрованные и отсортированные элементы
        self.filtered_items = self.filter_and_sort_items()

        if not self.filtered_items:
            # Показываем сообщение о пустом результате
            empty_label = QLabel("Нет данных для отображения")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_label.setStyleSheet("color: #999; font-size: 16px; padding: 40px;")
            self.scrollAreaLayout.addWidget(empty_label)
            self.scrollAreaLayout.addStretch()
            return

        hierarchy = self.group_hierarchically(self.filtered_items)

        # Сортируем организации: сначала ОАО МАЗ, потом остальные по алфавиту
        org_order = sorted(
            hierarchy.keys(),
            key=lambda x: (x != "ОАО МАЗ", x)
        )

        group_counter = 0
        for org_name in org_order:
            # Группа организации
            is_org_expanded = (group_counter == 0)
            org_group = CollapsibleGroup(org_name, is_org_expanded)
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

            # Типы подразделений внутри организации
            types = hierarchy[org_name]
            type_counter = 0
            for type_name, items in types.items():
                # Группа типа подразделения
                is_type_expanded = (type_counter == 0)
                type_group = CollapsibleGroup(type_name, is_type_expanded)
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

                # Карточки отделов
                for item in items:
                    # Получаем информацию о руководителе
                    leader_name = self._get_department_leader(item["id"])

                    card_data = {
                        "name": item["name"],
                        "code": str(item["id"]),
                        "leader": leader_name or "Не назначен",
                        "phone": f"{item['id']}00",
                        "description": f"{item['name']} ({item.get('parent_name', '')})"
                    }

                    item_card = DepartmentCard(card_data)
                    item_card.edit_clicked.connect(self.on_edit_department)
                    item_card.delete_clicked.connect(self.on_delete_department)

                    type_group.add_widget(item_card)

                org_group.add_widget(type_group)
                type_counter += 1

                # Обновляем высоту после добавления
                QTimer.singleShot(50, type_group._delayed_height_update)

            self.scrollAreaLayout.addWidget(org_group)
            group_counter += 1

            # Обновляем высоту организации после добавления всех типов
            if is_org_expanded:
                QTimer.singleShot(100, org_group._delayed_height_update)

        # Добавляем растяжку в конце
        self.scrollAreaLayout.addStretch()

        # Сбрасываем скролл в начало
        self.scrollArea.verticalScrollBar().setValue(0)
        self.scrollArea.update()

    def _get_department_leader(self, department_id):
        """Получает ФИО руководителя отдела (заглушка)"""
        # TODO: Реализовать получение из базы данных
        # Пока возвращаем None
        return None

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
        # Создаем диалог для добавления нового отдела
        dialog = DepartmentDialog(self)

        # Если пользователь нажал "Сохранить"
        if dialog.exec():
            # Получаем данные из диалога
            data = dialog.get_data()

            if data:
                # Здесь можно добавить логику сохранения в БД
                print(f"[DEBUG] Добавлен новый отдел: {data}")

                # Показываем сообщение об успехе
                QMessageBox.information(
                    self,
                    "Успешно",
                    f"Отдел '{data.get('name')}' успешно добавлен!"
                )

                # TODO: Обновить список отделов
                # self.refresh_departments()
            else:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Не удалось получить данные отдела"
                )

    def on_edit_department(self, data):
        """Обработчик редактирования отдела"""
        print(f"[DEBUG] Редактирование отдела: {data.get('name')}")

        # Ищем отдел в списке по ID
        department_id = data.get('id') or data.get('code')
        if department_id:
            # Пытаемся найти полные данные отдела
            department_data = None
            for item in self.all_items:
                if str(item.get('id')) == str(department_id):
                    department_data = {
                        'id': item.get('id'),
                        'name': item.get('name'),
                        'organization_id': item.get('organization_id'),
                        'parent_department_id': None,  # Пока нет родительского
                        'type_id': None,  # Пока нет типа
                        'department_number': str(item.get('id')),
                        'phone': '',  # Пока нет телефона
                        'head_id': None  # Пока нет руководителя
                    }
                    break

            # Если нашли данные, открываем диалог редактирования
            if department_data:
                dialog = DepartmentDialog(self, department_data=department_data)

                if dialog.exec():
                    # Получаем обновленные данные
                    updated_data = dialog.get_data()
                    print(f"[DEBUG] Обновлены данные отдела: {updated_data}")

                    # TODO: Сохранить изменения в БД
                    # self.update_department(updated_data)

                    QMessageBox.information(
                        self,
                        "Успешно",
                        f"Отдел '{updated_data.get('name')}' успешно обновлен!"
                    )

                    # TODO: Обновить список отделов
                    # self.refresh_departments()
                return

        # Если не нашли данные, открываем диалог создания с предзаполненными полями
        QMessageBox.warning(
            self,
            "Предупреждение",
            f"Данные отдела '{data.get('name')}' не найдены. Будет создан новый отдел."
        )
        self.on_add_department()

    def on_delete_department(self, item_id):
        """Обработчик удаления отдела"""
        print(f"[DEBUG] Удаление отдела с ID: {item_id}")

        # Ищем название отдела для сообщения
        department_name = f"ID: {item_id}"
        for item in self.all_items:
            if str(item.get('id')) == str(item_id):
                department_name = item.get('name', department_name)
                break

        # Подтверждение удаления
        reply = QMessageBox.question(
            self,
            "Подтверждение удаления",
            f"Вы уверены, что хотите удалить отдел '{department_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # TODO: Удалить из БД
            # self.delete_department(item_id)

            QMessageBox.information(
                self,
                "Успешно",
                f"Отдел '{department_name}' успешно удален!"
            )

            # TODO: Обновить список отделов
            # self.refresh_departments()


def main():
    """Точка входа для тестирования"""
    app = QApplication(sys.argv)

    # Тестовые данные
    test_data = [
        {
            "id": 1,
            "name": "ОАО МАЗ",
            "children": [
                {
                    "id": 2,
                    "name": "Отдел разработки",
                    "children": [
                        {"id": 3, "name": "Отдел ПО"},
                        {"id": 4, "name": "Отдел аппаратного обеспечения"}
                    ]
                },
                {
                    "id": 5,
                    "name": "Бухгалтерия",
                    "children": [
                        {"id": 6, "name": "Бухгалтерия расчетов"},
                        {"id": 7, "name": "Касса"}
                    ]
                }
            ]
        },
        {
            "id": 8,
            "name": "ООО ТехноСервис",
            "children": [
                {
                    "id": 9,
                    "name": "Отдел продаж",
                    "children": [
                        {"id": 10, "name": "Отдел оптовых продаж"}
                    ]
                }
            ]
        }
    ]

    window = DepartmentPage(structure_data=test_data)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()