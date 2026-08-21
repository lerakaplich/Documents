"""
Модуль управления иерархической структурой организаций и подразделений
"""

import os
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QComboBox, QCheckBox


# Определяем путь к папке с иконками
# Текущий файл: client/windows/system/employees/employee_dialog.py (или подобное)
# Поднимаемся на нужное количество уровней к корню проекта
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
ICONS_DIR = os.path.join(ROOT_DIR, "client", "icons")
# Для корректного отображения в CSS используем прямые слеши
ICONS_PATH_CSS = ICONS_DIR.replace('\\', '/')


class HierarchyManager:
    """Управляет динамической иерархией организаций и подразделений"""

    LEVEL_NAMES = {
        0: "Организация",
        1: "Подразделение",
        2: "Отдел",
        3: "Сектор",
        4: "Группа",
        5: "Участок",
    }

    def __init__(self, parent_dialog):
        self.parent = parent_dialog
        self.hierarchy_combos = []  # Список [(combo_widget, label_widget, level), ...]
        self.current_hierarchy_path = []  # Текущий путь [org_id, dep1_id, dep2_id, ...]
        self.leader_checkbox = None
        self.leader_checkbox_layout = None

        # Данные справочников
        self.organizations = {}
        self.departments_tree = {}
        self.all_departments = {}
        self.departments_by_org = {}
        self.root_departments = {}

    def build_departments_tree(self, departments):
        """Строит дерево подразделений из плоского списка"""
        print("[DEBUG] build_departments_tree() вызван")
        self.departments_tree = {}
        self.all_departments = {}

        for dept in departments:
            dept_id = dept['id']
            self.departments_tree[dept_id] = {
                'id': dept_id,
                'name': dept['name'],
                'parent_id': dept.get('parent_id'),
                'organization_id': dept.get('organization_id'),
                'children': []
            }
            self.all_departments[dept_id] = dept['name']

        for dept_id, dept_data in self.departments_tree.items():
            parent_id = dept_data['parent_id']
            if parent_id and parent_id in self.departments_tree:
                self.departments_tree[parent_id]['children'].append(dept_id)

    def group_departments_by_organization(self):
        """Группирует подразделения по организациям и находит корневые"""
        print("[DEBUG] group_departments_by_organization() вызван")
        self.departments_by_org = {}
        self.root_departments = {}

        for dept_id, dept_data in self.departments_tree.items():
            org_id = dept_data['organization_id']

            if org_id not in self.departments_by_org:
                self.departments_by_org[org_id] = []
            self.departments_by_org[org_id].append(dept_id)

            if dept_data['parent_id'] is None:
                if org_id not in self.root_departments:
                    self.root_departments[org_id] = []
                self.root_departments[org_id].append(dept_id)

    def get_children_for_parent(self, parent_id, organization_id=None):
        """Получает дочерние подразделения для указанного родителя"""
        if parent_id is None:
            return [(dept_id, self.departments_tree[dept_id]['name'])
                    for dept_id in self.root_departments.get(organization_id, [])
                    if dept_id in self.departments_tree]
        else:
            parent = self.departments_tree.get(parent_id, {})
            return [(child_id, self.departments_tree[child_id]['name'])
                    for child_id in parent.get('children', [])
                    if child_id in self.departments_tree]

    def get_level_name(self, level):
        """Возвращает название уровня"""
        return self.LEVEL_NAMES.get(level, f"Уровень {level}")

    def get_item_name(self, item_id):
        """Возвращает название элемента по его ID"""
        if item_id in self.organizations:
            return self.organizations[item_id]
        elif item_id in self.all_departments:
            return self.all_departments[item_id]
        return None

    def clear_hierarchy_layout(self):
        """Очищает динамические комбобоксы и их лейблы"""
        print("[DEBUG] clear_hierarchy_layout() вызван")
        print(f"[DEBUG] Количество элементов в hierarchyLayout до очистки: {self.parent.hierarchyLayout.count()}")

        while self.parent.hierarchyLayout.count():
            item = self.parent.hierarchyLayout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    child = item.layout().takeAt(0)
                    if child.widget():
                        child.widget().deleteLater()
                item.layout().deleteLater()
            elif item.widget():
                item.widget().deleteLater()

        self.hierarchy_combos = []
        self.current_hierarchy_path = []
        self.leader_checkbox = None
        self.leader_checkbox_layout = None

        print(f"[DEBUG] hierarchyLayout очищен, элементов: {self.parent.hierarchyLayout.count()}")

    def build_initial_hierarchy(self, filter_external_only=False, employee=None):
        """Строит начальную иерархию: Организация -> ... -> Руководитель в конце"""
        print("[DEBUG] build_initial_hierarchy() вызван")
        print(f"[DEBUG] Организаций для отображения: {len(self.organizations)}")

        self.clear_hierarchy_layout()

        # Добавляем организации
        org_items = [(org_id, org_name) for org_id, org_name in self.organizations.items()]
        if filter_external_only:
            org_items = [(org_id, org_name) for org_id, org_name in org_items if org_id != 1]

        if org_items:
            print("[DEBUG] Добавляем уровень 0 (Организация)")
            self.add_hierarchy_level(0, org_items)
        else:
            print("[WARNING] Список организаций пуст! Уровень 0 не добавлен")

        # Если редактируем сотрудника, устанавливаем выбранную организацию
        if employee and employee.get('organization_id'):
            org_id = employee.get('organization_id')
            if self.hierarchy_combos:
                combo = self.hierarchy_combos[0][0]
                index = combo.findData(org_id)
                if index >= 0:
                    combo.setCurrentIndex(index)
                    self.update_label_text(0, org_id)

        # Добавляем чекбокс руководителя
        self.add_leader_checkbox()
        self.update_leader_checkbox()

    def add_leader_checkbox(self):
        """Добавляет чекбокс руководителя после организации"""
        print("[DEBUG] add_leader_checkbox() вызван")

        row_layout = QHBoxLayout()
        row_layout.setSpacing(10)

        label = QLabel("")
        label.setMinimumSize(120, 0)
        label.setMaximumSize(120, 16777215)

        self.leader_checkbox = QCheckBox("Является руководителем организации")
        self.leader_checkbox.setMinimumSize(350, 0)
        self.leader_checkbox.setMaximumSize(350, 16777215)
        self.leader_checkbox.setStyleSheet("spacing: 8px; color: #1B232A;")
        self.leader_checkbox.setEnabled(False)
        self.leader_checkbox.toggled.connect(self.on_leader_toggled)

        row_layout.addWidget(label)
        row_layout.addWidget(self.leader_checkbox)
        row_layout.addStretch()

        self.leader_checkbox_layout = row_layout
        self.parent.hierarchyLayout.addLayout(row_layout)
        print("[DEBUG] Чекбокс руководителя добавлен")

    def add_hierarchy_level(self, level, items, selected_id=None):
        """Добавляет уровень иерархии (вставляет ПЕРЕД чекбоксом)"""
        print(f"[DEBUG] add_hierarchy_level(level={level}, items_count={len(items)})")

        row_layout = QHBoxLayout()
        row_layout.setSpacing(10)

        level_name = self.get_level_name(level)
        label = QLabel(f"{level_name}:")
        label.setMinimumSize(120, 0)
        label.setMaximumSize(120, 16777215)
        label.setStyleSheet("color: #1B232A; font-weight: 500;")
        label.setProperty("base_text", f"{level_name}:")

        combo = QComboBox()

        # Используем относительный путь к иконке через f-строку
        down_arrow_path = os.path.join(ICONS_DIR, "down_arrow.svg").replace('\\', '/')

        combo.setStyleSheet(f"""
            QComboBox {{
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 5px;
                background-color: white;
                color: #1B232A;
                font-size: 13px;
            }}
            QComboBox:hover {{
                border-color: #ccab6e;
            }}
            QComboBox:focus {{
                border: 2px solid #ccab6e;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border: none;
            }}
            QComboBox::down-arrow {{
                image: url("{down_arrow_path}");
                width: 16px;
                height: 16px;
                margin-right: 6px;
            }}
            QComboBox QAbstractItemView {{
                border-radius: 6px;
                background-color: white;
                color: #1B232A;
                padding: 4px;
                outline: none;
                border: 1px solid #ccab6e;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 8px;
                color: #1B232A;
                border: none;
                outline: none;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: #e3f2fd;
                color: #1B232A;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: #e3f2fd;
                color: #1B232A;
            }}
        """)

        combo.addItem("Не выбрано", None)
        for item_id, item_name in items:
            combo.addItem(item_name, item_id)

        combo.setProperty("level", level)
        if selected_id:
            index = combo.findData(selected_id)
            if index >= 0:
                combo.setCurrentIndex(index)

        combo.currentIndexChanged.connect(self.on_hierarchy_changed)

        row_layout.addWidget(label)
        row_layout.addWidget(combo)

        insert_index = self.parent.hierarchyLayout.count()
        if self.leader_checkbox_layout:
            leader_idx = self.parent.hierarchyLayout.indexOf(self.leader_checkbox_layout)
            if leader_idx != -1:
                insert_index = leader_idx

        self.parent.hierarchyLayout.insertLayout(insert_index, row_layout)

        self.hierarchy_combos.insert(level, (combo, label, level))

        for i in range(level + 1, len(self.hierarchy_combos)):
            self.hierarchy_combos[i] = (self.hierarchy_combos[i][0], self.hierarchy_combos[i][1], i)
            self.hierarchy_combos[i][0].setProperty("level", i)

        if selected_id:
            self.update_label_text(level, selected_id)

        return combo, label

    def remove_levels_after(self, level):
        """Удаляет все уровни иерархии ПОСЛЕ указанного"""
        print(f"[DEBUG] remove_levels_after(level={level})")

        while len(self.hierarchy_combos) > level + 1:
            combo, label, lvl = self.hierarchy_combos.pop()
            for i in range(self.parent.hierarchyLayout.count()):
                item = self.parent.hierarchyLayout.itemAt(i)
                if item and item.layout():
                    layout = item.layout()
                    found = False
                    for j in range(layout.count()):
                        if layout.itemAt(j).widget() == combo:
                            found = True
                            break
                    if found:
                        while layout.count():
                            widget = layout.takeAt(0).widget()
                            if widget:
                                widget.deleteLater()
                        self.parent.hierarchyLayout.removeItem(item)
                        break

    def on_hierarchy_changed(self, index):
        """Обработчик изменения значения в иерархическом комбобоксе"""
        print(f"[DEBUG] on_hierarchy_changed(index={index})")

        combo = self.parent.sender()
        if not combo: return

        level = combo.property("level")
        if level is None: return

        if self.leader_checkbox:
            self.leader_checkbox.blockSignals(True)

        selected_id = combo.currentData()
        print(f"[DEBUG] Уровень {level}, выбран ID: {selected_id}")

        self.current_hierarchy_path = self.current_hierarchy_path[:level]
        if selected_id:
            self.current_hierarchy_path.append(selected_id)

        self.update_label_text(level, selected_id)
        self.remove_levels_after(level)

        if selected_id:
            children = self.get_children_for_parent(selected_id)
            if children:
                self.add_hierarchy_level(level + 1, children)

        self.update_leader_checkbox()

        if self.leader_checkbox:
            self.leader_checkbox.blockSignals(False)

    def update_label_text(self, level, selected_id):
        """Обновляет текст метки для указанного уровня"""
        print(f"[DEBUG] update_label_text(level={level}, selected_id={selected_id})")

        if level < len(self.hierarchy_combos):
            combo, label, lvl = self.hierarchy_combos[level]
            base_text = label.property("base_text") or self.get_level_name(level) + ":"
            clean_base = base_text.rstrip(':')
            new_text = f"{clean_base}:"
            label.setText(new_text)
            print(f"[DEBUG] Метка обновлена на: '{new_text}'")

    def update_leader_checkbox(self):
        """Обновляет состояние и текст чекбокса руководителя"""
        if not self.leader_checkbox:
            return

        has_organization = len(self.current_hierarchy_path) > 0
        self.leader_checkbox.setEnabled(has_organization)

        if not has_organization:
            self.leader_checkbox.setChecked(False)
            self.leader_checkbox.setText("Является руководителем организации")
            return

        has_structural_units = len(self.hierarchy_combos) > 1

        if has_structural_units:
            last_combo = self.hierarchy_combos[-1][0]
            last_selected = last_combo.currentData()

            if last_selected:
                last_level = len(self.hierarchy_combos) - 1
                level_name = self.get_level_name(last_level).lower()
                item_name = self.get_item_name(last_selected)
                if item_name:
                    self.leader_checkbox.setText(f"Является руководителем «{item_name}»")
                else:
                    self.leader_checkbox.setText(f"Является руководителем {level_name}")
            else:
                prev_level = len(self.hierarchy_combos) - 2
                if prev_level >= 0:
                    level_name = self.get_level_name(prev_level).lower()
                    if prev_level < len(self.current_hierarchy_path):
                        prev_id = self.current_hierarchy_path[prev_level]
                        item_name = self.get_item_name(prev_id)
                        if item_name:
                            self.leader_checkbox.setText(f"Является руководителем «{item_name}»")
                        else:
                            self.leader_checkbox.setText(f"Является руководителем {level_name}")
                    else:
                        self.leader_checkbox.setText(f"Является руководителем {level_name}")
                else:
                    self.leader_checkbox.setText("Является руководителем организации")
        else:
            org_id = self.current_hierarchy_path[0]
            org_name = self.get_item_name(org_id)
            if org_name:
                self.leader_checkbox.setText(f"Является руководителем организации «{org_name}»")
            else:
                self.leader_checkbox.setText("Является руководителем организации")

    def on_leader_toggled(self, checked):
        """Обработчик переключения чекбокса руководителя"""
        print(f"[DEBUG] on_leader_toggled(checked={checked})")

        if checked:
            if len(self.current_hierarchy_path) == 0:
                self.leader_checkbox.setChecked(False)
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self.parent, "Предупреждение",
                                    "Для назначения руководителем необходимо выбрать организацию")
                return

            if len(self.hierarchy_combos) > 1:
                last_combo = self.hierarchy_combos[-1][0]
                last_selected = last_combo.currentData()

                if last_selected is None:
                    self.hide_last_level()
        else:
            self.show_last_level()

        self.update_leader_checkbox()

    def hide_last_level(self):
        """Скрывает последний уровень иерархии при отметке руководителя"""
        print("[DEBUG] hide_last_level() вызван")
        if len(self.hierarchy_combos) > 1:
            last_combo, last_label, last_level = self.hierarchy_combos[-1]

            for i in range(self.parent.hierarchyLayout.count()):
                item = self.parent.hierarchyLayout.itemAt(i)
                if item and item.layout():
                    layout = item.layout()
                    for j in range(layout.count()):
                        widget_item = layout.itemAt(j)
                        if widget_item and widget_item.widget() == last_combo:
                            for k in range(layout.count()):
                                hide_item = layout.itemAt(k)
                                if hide_item and hide_item.widget():
                                    hide_item.widget().hide()
                                    print("[DEBUG] Последний уровень скрыт")
                            return

    def show_last_level(self):
        """Показывает последний уровень иерархии при снятии отметки руководителя"""
        print("[DEBUG] show_last_level() вызван")
        if len(self.hierarchy_combos) > 1:
            last_combo, last_label, last_level = self.hierarchy_combos[-1]

            for i in range(self.parent.hierarchyLayout.count()):
                item = self.parent.hierarchyLayout.itemAt(i)
                if item and item.layout():
                    layout = item.layout()
                    for j in range(layout.count()):
                        widget_item = layout.itemAt(j)
                        if widget_item and widget_item.widget() == last_combo:
                            for k in range(layout.count()):
                                show_item = layout.itemAt(k)
                                if show_item and show_item.widget():
                                    show_item.widget().show()
                                    print("[DEBUG] Последний уровень показан")
                            return

    def get_current_hierarchy_path(self):
        """Возвращает текущий путь иерархии [org_id, dep1_id, dep2_id, ...]"""
        path = []
        for combo, label, level in self.hierarchy_combos:
            selected_id = combo.currentData()
            if selected_id:
                path.append(selected_id)
            else:
                break
        return path

    def set_test_data(self):
        """Заполняет тестовые данные для отладки"""
        print("[DEBUG] set_test_data() вызван")
        print("[INFO] Используются тестовые данные")

        self.organizations = {
            1: "ОАО МАЗ",
            2: "ООО Тестовая организация"
        }

        self.departments_tree = {
            1: {'id': 1, 'name': 'Управление информационных технологий', 'parent_id': None, 'organization_id': 1,
                'children': [2, 3]},
            2: {'id': 2, 'name': 'Отдел разработки', 'parent_id': 1, 'organization_id': 1, 'children': [4]},
            3: {'id': 3, 'name': 'Отдел тестирования', 'parent_id': 1, 'organization_id': 1, 'children': []},
            4: {'id': 4, 'name': 'Группа бэкенда', 'parent_id': 2, 'organization_id': 1, 'children': []},
            5: {'id': 5, 'name': 'Управление продаж', 'parent_id': None, 'organization_id': 2, 'children': [6]},
            6: {'id': 6, 'name': 'Отдел прямых продаж', 'parent_id': 5, 'organization_id': 2, 'children': []},
        }

        self.all_departments = {
            1: 'Управление информационных технологий',
            2: 'Отдел разработки',
            3: 'Отдел тестирования',
            4: 'Группа бэкенда',
            5: 'Управление продаж',
            6: 'Отдел прямых продаж'
        }

        self.departments_by_org = {
            1: [1, 2, 3, 4],
            2: [5, 6]
        }

        self.root_departments = {
            1: [1],
            2: [5]
        }