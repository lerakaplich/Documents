







"""
Диалог создания/редактирования сотрудника
UI загружается из .ui файла
Поддерживает динамическую древовидную структуру подразделений
"""

import os
import asyncio
from datetime import date
from PyQt6 import QtWidgets, uic, QtCore
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtWidgets import QMessageBox, QHBoxLayout, QLabel, QComboBox, QCheckBox


class EmployeeDialog(QtWidgets.QDialog):
    """Диалог создания/редактирования сотрудника"""

    employee_created = pyqtSignal(int)
    employee_updated = pyqtSignal(int)

    # Словарь с типами структурных единиц для отображения
    LEVEL_NAMES = {
        0: "Организация",
        1: "Подразделение",
        2: "Отдел",
        3: "Сектор",
        4: "Группа",
        5: "Участок",
        # Можно добавлять новые уровни
    }

    def __init__(self, parent_editor=None, employee=None, is_maz=False, profile_manager=None,
                 current_user_rights='user', current_user_org_id=None, current_user_div_id=None,
                 current_user_dept_id=None, is_organization_head=False, is_division_head=False,
                 is_department_head=False, filter_external_only=False, organization_head_ids=None):
        super().__init__(parent_editor)

        # Сохраняем данные
        self.employee = employee if employee is not None else {}
        self.is_maz = is_maz
        self.profile_manager = profile_manager
        self.current_user_rights = current_user_rights
        self.current_user_org_id = current_user_org_id
        self.current_user_div_id = current_user_div_id
        self.current_user_dept_id = current_user_dept_id
        self.is_organization_head = is_organization_head
        self.is_division_head = is_division_head
        self.is_department_head = is_department_head
        self.filter_external_only = filter_external_only
        self.organization_head_ids = organization_head_ids or []

        # Данные справочников
        self.organizations = {}  # {id: name}
        self.departments_tree = {}  # {id: {'name': name, 'parent_id': parent_id, 'children': []}}
        self.all_departments = {}  # {id: name} для быстрого доступа
        self.departments_by_org = {}  # {organization_id: [list of department_ids]}
        self.root_departments = {}  # {organization_id: [list of root department_ids]}

        # Динамические комбобоксы для иерархии
        self.hierarchy_combos = []  # Список [(combo_widget, label_widget), ...]
        self.current_hierarchy_path = []  # Текущий путь [org_id, dep1_id, dep2_id, ...]

        # Чекбокс руководителя (динамический)
        self.leader_checkbox = None
        self.leader_checkbox_layout = None

        self._data_loaded = False

        # Загружаем UI
        self._load_ui()

        # Настраиваем окно
        self._setup_window()

        # Подключаем сигналы
        self._connect_signals()

        # Загружаем данные
        self._load_initial_data()

    def _load_initial_data(self):
        """Загружает начальные данные"""
        if self.profile_manager:
            # Пробуем асинхронную загрузку
            try:
                loop = asyncio.get_running_loop()
                # Есть running loop - создаем задачу
                loop.create_task(self._load_data_async())
            except RuntimeError:
                # Нет running loop - используем QTimer для отложенной загрузки
                QTimer.singleShot(100, self._load_data_sync)
        else:
            # Нет profile_manager - используем тестовые данные
            self._fill_test_data()

    def _load_data_sync(self):
        """Синхронная загрузка данных (для случаев без event loop)"""
        try:
            # Запускаем asyncio в отдельном потоке через QTimer
            asyncio.run(self._load_data_async())
        except Exception as e:
            print(f"[ERROR] Ошибка синхронной загрузки: {e}")
            import traceback
            traceback.print_exc()
            # В случае ошибки используем тестовые данные
            self._fill_test_data()

    async def _load_data_async(self):
        """Асинхронная загрузка данных справочников"""
        try:
            print("[INFO] Начало загрузки данных...")

            if self.profile_manager:
                await self.profile_manager.initialize()

                # Загружаем организации
                orgs = await self.profile_manager.get_all_organizations()
                self.organizations = {org['id']: org['name'] for org in orgs}
                print(f"[INFO] Загружено организаций: {len(self.organizations)}")

                # Загружаем все подразделения
                depts = await self.profile_manager.get_all_departments()

                # Строим дерево подразделений
                self._build_departments_tree(depts)
                print(f"[INFO] Загружено подразделений: {len(self.departments_tree)}")

                # Группируем подразделения по организациям
                self._group_departments_by_organization()

            self._data_loaded = True

            # Обновляем UI в главном потоке
            self._build_initial_hierarchy()

            # Если редактируем сотрудника, заполняем данные
            if self.employee:
                self._fill_employee_data()

        except Exception as e:
            print(f"[ERROR] Ошибка загрузки данных: {e}")
            import traceback
            traceback.print_exc()
            # Используем тестовые данные при ошибке
            self._fill_test_data()

    def _load_ui(self):
        """Загружает UI из .ui файла"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(
            current_dir, '..', '..', '..', 'ui', 'system', 'employees', 'employee_dialog.ui'
        )
        ui_path = os.path.normpath(ui_path)

        if not os.path.exists(ui_path):
            raise FileNotFoundError(f"UI file not found: {ui_path}")

        uic.loadUi(ui_path, self)

    def _setup_window(self):
        """Настраивает заголовок окна"""
        is_edit = self.employee and self.employee.get('id')

        if is_edit:
            full_name = f"{self.employee.get('last_name', '')} {self.employee.get('first_name', '')}"
            self.setWindowTitle(f"Редактирование сотрудника - {full_name}")
            self.titleLabel.setText(f"Редактирование сотрудника")
        else:
            self.setWindowTitle("Новый сотрудник")
            self.titleLabel.setText("Новый сотрудник")

        self.resize(750, 850)

        # Настройка комбобоксов, не зависящих от данных
        self._setup_static_comboboxes()

    def _setup_static_comboboxes(self):
        """Настраивает статические комбобоксы"""
        # Тип назначения
        self.assignmentTypeCombo.clear()
        self.assignmentTypeCombo.addItem("Основное", "primary")
        self.assignmentTypeCombo.addItem("Совместительство", "part_time")
        self.assignmentTypeCombo.addItem("Исполняющий обязанности", "acting_director")

        # Права доступа
        self.rightsCombo.clear()
        self.rightsCombo.addItem("Пользователь", "user")

        if self.current_user_rights in ['admin', 'superadmin']:
            self.rightsCombo.addItem("Администратор", "admin")

        # Скрываем старый чекбокс руководителя (он будет динамическим)
        self.isLeaderCheckbox.hide()

    def _connect_signals(self):
        """Подключает сигналы"""
        self.saveButton.clicked.connect(self.save)


    def _build_departments_tree(self, departments):
        """
        Строит дерево подразделений из плоского списка

        Args:
            departments: список отделов вида [{'id': 1, 'name': '...', 'parent_id': None, 'organization_id': 1}, ...]
        """
        self.departments_tree = {}
        self.all_departments = {}

        # Сначала создаём все узлы
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

        # Затем строим связи родитель-ребёнок
        for dept_id, dept_data in self.departments_tree.items():
            parent_id = dept_data['parent_id']
            if parent_id and parent_id in self.departments_tree:
                self.departments_tree[parent_id]['children'].append(dept_id)

    def _group_departments_by_organization(self):
        """Группирует подразделения по организациям и находит корневые"""
        self.departments_by_org = {}
        self.root_departments = {}

        for dept_id, dept_data in self.departments_tree.items():
            org_id = dept_data['organization_id']

            # Группировка по организациям
            if org_id not in self.departments_by_org:
                self.departments_by_org[org_id] = []
            self.departments_by_org[org_id].append(dept_id)

            # Корневые подразделения (родитель = None)
            if dept_data['parent_id'] is None:
                if org_id not in self.root_departments:
                    self.root_departments[org_id] = []
                self.root_departments[org_id].append(dept_id)

    def _get_children_for_parent(self, parent_id, organization_id=None):
        """
        Получает дочерние подразделения для указанного родителя

        Args:
            parent_id: ID родительского подразделения (None для корневых)
            organization_id: ID организации (если parent_id is None)

        Returns:
            list: [(dept_id, dept_name), ...]
        """
        if parent_id is None:
            # Возвращаем корневые подразделения организации
            return [(dept_id, self.departments_tree[dept_id]['name'])
                    for dept_id in self.root_departments.get(organization_id, [])
                    if dept_id in self.departments_tree]
        else:
            # Возвращаем дочерние подразделения
            parent = self.departments_tree.get(parent_id, {})
            return [(child_id, self.departments_tree[child_id]['name'])
                    for child_id in parent.get('children', [])
                    if child_id in self.departments_tree]

    def _get_level_name(self, level):
        """Возвращает название уровня"""
        return self.LEVEL_NAMES.get(level, f"Уровень {level}")

    def _build_initial_hierarchy(self):
        """Строит начальную иерархию: Организация -> Руководитель"""
        # Очищаем существующую иерархию
        self._clear_hierarchy()

        # Добавляем первый уровень - Организация
        org_items = [(org_id, org_name) for org_id, org_name in self.organizations.items()]
        if self.filter_external_only:
            # Если показываем только внешние организации, исключаем МАЗ (id=1)
            org_items = [(org_id, org_name) for org_id, org_name in org_items if org_id != 1]

        self._add_hierarchy_level(0, None, "Организация *:", org_items)

        # Добавляем чекбокс "Руководитель" сразу после организации
        self._add_leader_checkbox()

        # Если редактируем сотрудника, устанавливаем выбранную организацию
        if self.employee and self.employee.get('organization_id'):
            org_id = self.employee.get('organization_id')
            if self.hierarchy_combos:
                combo = self.hierarchy_combos[0][0]
                index = combo.findData(org_id)
                if index >= 0:
                    combo.setCurrentIndex(index)

    def _add_leader_checkbox(self):
        """Добавляет чекбокс руководителя после организации"""
        # Создаем layout для чекбокса
        row_layout = QHBoxLayout()
        row_layout.setSpacing(10)

        # Пустая метка для выравнивания
        label = QLabel("")
        label.setMinimumSize(120, 0)

        # Создаем чекбокс
        self.leader_checkbox = QCheckBox("Является руководителем организации")
        self.leader_checkbox.setStyleSheet("spacing: 8px; color: #1B232A;")
        self.leader_checkbox.setEnabled(False)  # Изначально неактивен (нет выбранной организации)
        self.leader_checkbox.toggled.connect(self._on_leader_toggled)

        # Добавляем в layout
        row_layout.addWidget(label)
        row_layout.addWidget(self.leader_checkbox)

        # Сохраняем layout для последующего удаления/обновления
        self.leader_checkbox_layout = row_layout

        # Добавляем в основной layout
        self.hierarchyLayout.addLayout(row_layout)

    def _update_leader_checkbox(self):
        """Обновляет состояние и текст чекбокса руководителя"""
        if not self.leader_checkbox:
            return

        # Чекбокс активен, только если выбрана организация
        has_organization = len(self.current_hierarchy_path) > 0
        self.leader_checkbox.setEnabled(has_organization)

        if not has_organization:
            self.leader_checkbox.setChecked(False)
            self.leader_checkbox.setText("Является руководителем организации")
            return

        # Определяем, есть ли выбранные структурные единицы
        has_structural_units = len(self.current_hierarchy_path) > 1

        if has_structural_units:
            # Есть выбранные подразделения - показываем последний уровень
            last_level = len(self.current_hierarchy_path) - 1
            level_name = self._get_level_name(last_level).lower()
            self.leader_checkbox.setText(f"Является руководителем {level_name}")
        else:
            # Только организация
            self.leader_checkbox.setText("Является руководителем организации")

    def _clear_hierarchy(self):
        """Очищает все динамические элементы иерархии"""
        # Удаляем все виджеты из hierarchyLayout
        while self.hierarchyLayout.count():
            item = self.hierarchyLayout.takeAt(0)
            if item.layout():
                # Удаляем все элементы из вложенного layout
                while item.layout().count():
                    sub_item = item.layout().takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()
                item.layout().deleteLater()

        self.hierarchy_combos = []
        self.current_hierarchy_path = []
        self.leader_checkbox = None
        self.leader_checkbox_layout = None

    def _add_hierarchy_level(self, level, parent_id, label_text, items):
        """
        Добавляет уровень иерархии

        Args:
            level: Уровень вложенности (0 - организация, 1 - подразделение, ...)
            parent_id: ID родительского элемента
            label_text: Текст метки
            items: Список [(id, name), ...] для комбобокса
        """
        # Создаем layout для строки
        row_layout = QHBoxLayout()
        row_layout.setSpacing(10)

        # Создаем метку
        label = QLabel(label_text)
        label.setMinimumSize(120, 0)
        label.setStyleSheet("color: #1B232A; font-weight: 500;")

        # Создаем комбобокс
        combo = QComboBox()
        combo.setStyleSheet("border: 1px solid #dee2e6; border-radius: 6px; padding: 5px; background-color: white;")
        combo.addItem("Не выбрано", None)

        for item_id, item_name in items:
            combo.addItem(item_name, item_id)

        # Подключаем сигнал изменения
        combo.currentIndexChanged.connect(
            lambda idx, lvl=level, cb=combo: self._on_hierarchy_changed(lvl, cb)
        )

        # Добавляем в layout
        row_layout.addWidget(label)
        row_layout.addWidget(combo)

        # Определяем позицию для вставки
        # Если это уровень 0 (организация) - вставляем в начало
        # Иначе - вставляем перед чекбоксом руководителя
        if level == 0:
            self.hierarchyLayout.insertLayout(0, row_layout)
            self.hierarchy_combos.insert(0, (combo, label))
        else:
            # Находим позицию чекбокса руководителя
            checkbox_position = self.hierarchyLayout.indexOf(self.leader_checkbox_layout)
            if checkbox_position >= 0:
                # Вставляем перед чекбоксом
                insert_position = checkbox_position
                self.hierarchyLayout.insertLayout(insert_position, row_layout)
                self.hierarchy_combos.insert(level, (combo, label))
            else:
                # Если чекбокса нет, добавляем в конец
                self.hierarchyLayout.addLayout(row_layout)
                self.hierarchy_combos.append((combo, label))

        return combo, label

    def _on_hierarchy_changed(self, level, combo):
        """
        Обработчик изменения значения в иерархическом комбобоксе

        Args:
            level: Уровень, который изменился
            combo: Комбобокс, который изменился
        """
        # Блокируем сигналы чекбокса, чтобы избежать рекурсии
        if self.leader_checkbox:
            self.leader_checkbox.blockSignals(True)

        # Получаем выбранное значение
        selected_id = combo.currentData()

        # Обновляем путь
        self.current_hierarchy_path = self.current_hierarchy_path[:level]
        if selected_id:
            self.current_hierarchy_path.append(selected_id)

        # Проверяем, была ли выбрана последняя единица перед изменением
        last_was_selected = len(self.current_hierarchy_path) > level and self.current_hierarchy_path[-1] is not None

        # Удаляем все уровни после текущего
        self._remove_levels_after(level)

        # Сбрасываем чекбокс руководителя при изменении структуры
        if self.leader_checkbox:
            self.leader_checkbox.setChecked(False)

        # Если что-то выбрано и это не "Не выбрано"
        if selected_id:
            children = self._get_children_for_parent(selected_id)
            if children:
                next_level = level + 1
                label_text = f"{self._get_level_name(next_level)}:"
                self._add_hierarchy_level(next_level, selected_id, label_text, children)

        # Обновляем чекбокс руководителя
        self._update_leader_checkbox()

        # Разблокируем сигналы чекбокса
        if self.leader_checkbox:
            self.leader_checkbox.blockSignals(False)

    def _on_leader_toggled(self, checked):
        """Обработчик переключения чекбокса руководителя"""
        if checked:
            # Если отмечен как руководитель, проверяем что выбрана организация
            if len(self.current_hierarchy_path) == 0:
                self.leader_checkbox.setChecked(False)
                QMessageBox.warning(self, "Предупреждение",
                                    "Для назначения руководителем необходимо выбрать организацию")
                return

            # Проверяем, выбрана ли последняя структурная единица
            if len(self.hierarchy_combos) > 1:
                last_combo = self.hierarchy_combos[-1][0]
                last_selected = last_combo.currentData()

                # Если последняя единица НЕ выбрана - скрываем её
                if last_selected is None:
                    self._hide_last_level()
                # Если выбрана - оставляем видимой (сотрудник становится руководителем этой единицы)
        else:
            # Показываем последний уровень (если был скрыт)
            self._show_last_level()

        # Обновляем текст чекбокса
        self._update_leader_checkbox_text_after_toggle(checked)

    def _update_leader_checkbox(self):
        """Обновляет состояние и текст чекбокса руководителя"""
        if not self.leader_checkbox:
            return

        # Чекбокс активен, только если выбрана организация
        has_organization = len(self.current_hierarchy_path) > 0
        self.leader_checkbox.setEnabled(has_organization)

        if not has_organization:
            self.leader_checkbox.setChecked(False)
            self.leader_checkbox.setText("Является руководителем организации")
            return

        # Определяем, есть ли выбранные структурные единицы
        has_structural_units = len(self.hierarchy_combos) > 1

        if has_structural_units:
            # Проверяем, выбрана ли последняя единица
            last_combo = self.hierarchy_combos[-1][0]
            last_selected = last_combo.currentData()

            if last_selected:
                # Последняя единица выбрана - показываем её уровень
                last_level = len(self.hierarchy_combos) - 1
                level_name = self._get_level_name(last_level).lower()
                self.leader_checkbox.setText(f"Является руководителем {level_name}")
            else:
                # Последняя единица не выбрана - показываем предыдущий уровень
                prev_level = len(self.hierarchy_combos) - 2
                if prev_level >= 0:
                    level_name = self._get_level_name(prev_level).lower()
                    self.leader_checkbox.setText(f"Является руководителем {level_name}")
                else:
                    self.leader_checkbox.setText("Является руководителем организации")
        else:
            # Только организация
            self.leader_checkbox.setText("Является руководителем организации")

    def _update_leader_checkbox_text_after_toggle(self, checked):
        """Обновляет текст чекбокса после переключения"""
        if not self.leader_checkbox:
            return

        if not checked:
            # Если сняли галку - возвращаем стандартный текст
            self._update_leader_checkbox()
            return

        # Если поставили галку
        has_structural_units = len(self.hierarchy_combos) > 1

        if has_structural_units:
            last_combo = self.hierarchy_combos[-1][0]
            last_selected = last_combo.currentData()

            if last_selected:
                # Последняя единица выбрана - руководитель этой единицы
                last_level = len(self.hierarchy_combos) - 1
                level_name = self._get_level_name(last_level).lower()
                self.leader_checkbox.setText(f"Является руководителем {level_name}")
            else:
                # Последняя единица не выбрана и скрыта - руководитель предыдущей
                prev_level = len(self.hierarchy_combos) - 2
                if prev_level >= 0:
                    level_name = self._get_level_name(prev_level).lower()
                    self.leader_checkbox.setText(f"Является руководителем {level_name}")
                else:
                    self.leader_checkbox.setText("Является руководителем организации")
        else:
            # Только организация выбрана
            self.leader_checkbox.setText("Является руководителем организации")

    def _hide_last_level(self):
        """Скрывает последний уровень иерархии при отметке руководителя"""
        if len(self.hierarchy_combos) > 1:  # Есть что скрывать (кроме организации)
            last_combo, last_label = self.hierarchy_combos[-1]

            # Находим layout последнего уровня
            for i in range(self.hierarchyLayout.count()):
                item = self.hierarchyLayout.itemAt(i)
                if item and item.layout():
                    layout = item.layout()
                    # Проверяем, содержит ли этот layout последний комбобокс
                    for j in range(layout.count()):
                        widget_item = layout.itemAt(j)
                        if widget_item and widget_item.widget() == last_combo:
                            # Скрываем все виджеты в этом layout
                            for k in range(layout.count()):
                                hide_item = layout.itemAt(k)
                                if hide_item and hide_item.widget():
                                    hide_item.widget().hide()
                            return

    def _show_last_level(self):
        """Показывает последний уровень иерархии при снятии отметки руководителя"""
        if len(self.hierarchy_combos) > 1:  # Есть что показывать (кроме организации)
            last_combo, last_label = self.hierarchy_combos[-1]

            # Находим layout последнего уровня
            for i in range(self.hierarchyLayout.count()):
                item = self.hierarchyLayout.itemAt(i)
                if item and item.layout():
                    layout = item.layout()
                    # Проверяем, содержит ли этот layout последний комбобокс
                    for j in range(layout.count()):
                        widget_item = layout.itemAt(j)
                        if widget_item and widget_item.widget() == last_combo:
                            # Показываем все виджеты в этом layout
                            for k in range(layout.count()):
                                show_item = layout.itemAt(k)
                                if show_item and show_item.widget():
                                    show_item.widget().show()
                            return

    def get_data(self):
        """Возвращает данные из формы"""
        rights_index = self.rightsCombo.currentIndex()
        rights = self.rightsCombo.itemData(rights_index) or 'user' if rights_index >= 0 else 'user'

        assignment_index = self.assignmentTypeCombo.currentIndex()
        assignment_kind = self.assignmentTypeCombo.itemData(
            assignment_index) or 'primary' if assignment_index >= 0 else 'primary'

        # Получаем путь иерархии (только выбранные элементы, без "Не выбрано")
        hierarchy_path = self._get_current_hierarchy_path()

        # Определяем department_id
        is_leader = self.leader_checkbox.isChecked() if self.leader_checkbox else False

        if is_leader:
            # Если руководитель
            if len(self.hierarchy_combos) > 1:
                last_combo = self.hierarchy_combos[-1][0]
                last_selected = last_combo.currentData()

                if last_selected:
                    # Последняя единица выбрана - руководитель этой единицы
                    department_id = last_selected
                else:
                    # Последняя единица не выбрана - руководитель предыдущей
                    if len(self.hierarchy_combos) > 2:
                        prev_combo = self.hierarchy_combos[-2][0]
                        department_id = prev_combo.currentData()
                    else:
                        department_id = None
            else:
                # Только организация - руководитель организации
                department_id = None
        else:
            # Не руководитель - берем последний выбранный элемент
            department_id = hierarchy_path[-1] if hierarchy_path else None

        organization_id = hierarchy_path[0] if hierarchy_path else None

        chat_id_text = self.chatIdEdit.text().strip()
        chat_id = int(chat_id_text) if chat_id_text and chat_id_text.isdigit() else None

        data = {
            'last_name': self.lastNameEdit.text().strip(),
            'first_name': self.firstNameEdit.text().strip(),
            'patronymic': self.patronymicEdit.text().strip(),
            'phone_number': self.phoneEdit.text().strip(),
            'work_number': self.workPhoneEdit.text().strip(),
            'email': self.emailEdit.text().strip(),
            'birth_date': self.birthDateEdit.date().toPyDate(),
            'chat_id': chat_id,
            'organization_id': organization_id,
            'department_id': department_id,
            'hierarchy_path': hierarchy_path,
            'position_name': self.positionEdit.text().strip(),
            'assignment_kind': assignment_kind,
            'is_leader': is_leader,
            'rights': rights,
            'is_active': True
        }

        if self.employee and self.employee.get('id'):
            data['id'] = self.employee['id']

        return data

    def _get_current_hierarchy_path(self):
        """Возвращает текущий путь иерархии [org_id, dep1_id, dep2_id, ...]"""
        path = []
        for combo, label in self.hierarchy_combos:
            selected_id = combo.currentData()
            if selected_id:
                path.append(selected_id)
            else:
                break
        return path

    def _remove_levels_after(self, level):
        """Удаляет все уровни иерархии после указанного"""
        # Удаляем комбобоксы из списка и layout
        while len(self.hierarchy_combos) > level + 1:
            # Получаем последний элемент
            last_combo, last_label = self.hierarchy_combos[-1]

            # Находим layout, содержащий этот комбобокс
            for i in range(self.hierarchyLayout.count()):
                item = self.hierarchyLayout.itemAt(i)
                if item and item.layout():
                    # Проверяем, содержит ли этот layout наш комбобокс
                    layout = item.layout()
                    for j in range(layout.count()):
                        widget_item = layout.itemAt(j)
                        if widget_item and widget_item.widget() == last_combo:
                            # Удаляем виджеты
                            while layout.count():
                                sub_item = layout.takeAt(0)
                                if sub_item.widget():
                                    sub_item.widget().deleteLater()
                            # Удаляем layout
                            self.hierarchyLayout.removeItem(item)
                            layout.deleteLater()
                            break
                    else:
                        continue
                    break

            # Удаляем из списка
            self.hierarchy_combos.pop()

    def _fill_test_data(self):
        """Заполняет тестовые данные для отладки"""
        print("[INFO] Используются тестовые данные")
        self.organizations = {
            1: "ОАО МАЗ",
            2: "ООО Тестовая организация"
        }

        # Тестовое дерево подразделений (может быть любой глубины)
        self.departments_tree = {
            # МАЗ: Управление -> Отдел -> Группа
            1: {'id': 1, 'name': 'Управление информационных технологий', 'parent_id': None, 'organization_id': 1, 'children': [2, 3]},
            2: {'id': 2, 'name': 'Отдел разработки', 'parent_id': 1, 'organization_id': 1, 'children': [4]},
            3: {'id': 3, 'name': 'Отдел тестирования', 'parent_id': 1, 'organization_id': 1, 'children': []},
            4: {'id': 4, 'name': 'Группа бэкенда', 'parent_id': 2, 'organization_id': 1, 'children': []},

            # Тестовая: просто Подразделение -> Отдел
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

        # Группировка по организациям
        self.departments_by_org = {
            1: [1, 2, 3, 4],
            2: [5, 6]
        }

        # Корневые подразделения
        self.root_departments = {
            1: [1],
            2: [5]
        }

        self._data_loaded = True
        self._build_initial_hierarchy()

        # Если редактируем, заполняем данные
        if self.employee:
            self._fill_employee_data()

    def _fill_employee_data(self):
        """Заполняет поля данными сотрудника"""
        if not self.employee or not self._data_loaded:
            return

        print("[INFO] Заполнение данных сотрудника...")

        # Личная информация
        self.lastNameEdit.setText(self.employee.get('last_name', ''))
        self.firstNameEdit.setText(self.employee.get('first_name', ''))
        self.patronymicEdit.setText(self.employee.get('patronymic', ''))
        self.serviceNumberEdit.setText(self.employee.get('service_number', ''))

        # Дата рождения
        birth_date = self.employee.get('birth_date')
        if birth_date:
            if isinstance(birth_date, str):
                from datetime import datetime
                try:
                    birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
                except:
                    birth_date = date(1980, 1, 1)
            self.birthDateEdit.setDate(birth_date)
        else:
            self.birthDateEdit.setDate(date(1980, 1, 1))

        # Контакты
        self.phoneEdit.setText(self.employee.get('phone_number', ''))
        self.workPhoneEdit.setText(self.employee.get('work_number', ''))
        self.emailEdit.setText(self.employee.get('email', ''))
        chat_id = self.employee.get('chat_id')
        self.chatIdEdit.setText(str(chat_id) if chat_id else '')

        # Рабочая информация
        self.positionEdit.setText(self.employee.get('position_name', ''))

        # Тип назначения
        assignment_type = self.employee.get('assignment_kind', 'primary')
        for i in range(self.assignmentTypeCombo.count()):
            if self.assignmentTypeCombo.itemData(i) == assignment_type:
                self.assignmentTypeCombo.setCurrentIndex(i)
                break

        # Права
        rights = self.employee.get('rights', 'user')
        for i in range(self.rightsCombo.count()):
            if self.rightsCombo.itemData(i) == rights:
                self.rightsCombo.setCurrentIndex(i)
                break

        # Иерархия и руководитель
        is_leader = self.employee.get('is_leader', False)
        hierarchy_path = self.employee.get('hierarchy_path', [])

        if hierarchy_path:
            # Устанавливаем значения в комбобоксы
            for level, item_id in enumerate(hierarchy_path):
                if level < len(self.hierarchy_combos):
                    combo = self.hierarchy_combos[level][0]
                    index = combo.findData(item_id)
                    if index >= 0:
                        combo.setCurrentIndex(index)

            # Если руководитель, отмечаем чекбокс
            if is_leader and self.leader_checkbox:
                self.leader_checkbox.setChecked(True)

        elif self.employee.get('organization_id'):
            # Старый формат данных
            org_id = self.employee.get('organization_id')
            dept_id = self.employee.get('department_id')

            # Устанавливаем организацию
            if self.hierarchy_combos:
                combo = self.hierarchy_combos[0][0]
                index = combo.findData(org_id)
                if index >= 0:
                    combo.setCurrentIndex(index)

            # Ждем построения иерархии и устанавливаем department
            if dept_id:
                QTimer.singleShot(500, lambda: self._set_old_format_data(dept_id, is_leader))

    def _set_old_format_data(self, dept_id, is_leader):
        """Устанавливает данные из старого формата"""
        if dept_id in self.departments_tree:
            # Строим путь от dept_id до корня
            path = []
            current_id = dept_id
            while current_id:
                path.insert(0, current_id)
                current_id = self.departments_tree[current_id]['parent_id']

            # Устанавливаем значения в комбобоксы (пропускаем организацию)
            for level, item_id in enumerate(path):
                combo_level = level + 1  # +1 потому что 0 - организация
                if combo_level < len(self.hierarchy_combos):
                    combo = self.hierarchy_combos[combo_level][0]
                    index = combo.findData(item_id)
                    if index >= 0:
                        combo.setCurrentIndex(index)

            # Если руководитель, отмечаем чекбокс
            if is_leader and self.leader_checkbox:
                self.leader_checkbox.setChecked(True)

    def validate(self):
        """Валидация данных"""
        errors = []

        if not self.lastNameEdit.text().strip():
            errors.append("Фамилия обязательна для заполнения")

        if not self.firstNameEdit.text().strip():
            errors.append("Имя обязательно для заполнения")

        if not self.positionEdit.text().strip():
            errors.append("Должность обязательна для заполнения")

        # Проверяем, что выбрана хотя бы организация
        hierarchy_path = self._get_current_hierarchy_path()
        if not hierarchy_path:
            errors.append("Организация обязательна для заполнения")

        return errors

    def save(self):
        """Сохраняет данные"""
        errors = self.validate()
        if errors:
            QMessageBox.warning(self, "Ошибка валидации", "\n".join(errors))
            return

        data = self.get_data()
        is_edit = self.employee and self.employee.get('id')

        if is_edit:
            self._start_async_update(data)
        else:
            self._start_async_create(data)

    def _start_async_create(self, data):
        """Запускает асинхронное создание сотрудника"""
        if self.profile_manager:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._create_employee(data))
            except RuntimeError:
                asyncio.run(self._create_employee(data))
        else:
            # Тестовый режим
            print(f"[TEST] Создание сотрудника: {data}")
            self.accept()

    def _start_async_update(self, data):
        """Запускает асинхронное обновление сотрудника"""
        if self.profile_manager:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._update_employee(data))
            except RuntimeError:
                asyncio.run(self._update_employee(data))
        else:
            # Тестовый режим
            print(f"[TEST] Обновление сотрудника: {data}")
            self.accept()

    async def _create_employee(self, data):
        """Асинхронное создание сотрудника"""
        try:
            from datetime import datetime
            data['service_number'] = f"EMP_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            if self.profile_manager:
                employee_id = await self.profile_manager.add_employee(data)
                if employee_id:
                    self.employee_created.emit(employee_id)
                    self.accept()
                else:
                    self._show_error("Не удалось создать сотрудника")
            else:
                print(f"[TEST] Создание сотрудника: {data}")
                self.accept()

        except Exception as e:
            print(f"[ERROR] Ошибка создания сотрудника: {e}")
            self._show_error(f"Ошибка: {str(e)}")

    async def _update_employee(self, data):
        """Асинхронное обновление сотрудника"""
        try:
            employee_id = self.employee['id']

            if self.profile_manager:
                success = await self.profile_manager.update_employee(employee_id, data)
                if success:
                    self.employee_updated.emit(employee_id)
                    self.accept()
                else:
                    self._show_error("Не удалось обновить данные сотрудника")
            else:
                print(f"[TEST] Обновление сотрудника {employee_id}: {data}")
                self.accept()

        except Exception as e:
            print(f"[ERROR] Ошибка обновления сотрудника: {e}")
            self._show_error(f"Ошибка: {str(e)}")

    def _show_error(self, message):
        """Показывает ошибку"""
        QMessageBox.critical(self, "Ошибка", message)

    def closeEvent(self, event):
        """Обработчик закрытия окна"""
        super().closeEvent(event)


# Тестовый запуск
if __name__ == '__main__':
    import sys

    app = QtWidgets.QApplication(sys.argv)

    # Тест 1: Создание нового сотрудника
    print("=" * 50)
    print("Тест 1: Создание нового сотрудника")
    print("=" * 50)

    dialog = EmployeeDialog(
        parent_editor=None,
        employee=None,
        current_user_rights='admin'
    )
    dialog.show()

    sys.exit(app.exec())





















# """
# Диалог создания/редактирования сотрудника
# UI загружается из .ui файла
# Поддерживает динамическую древовидную структуру подразделений
# Использует модуль core для иерархии и валидации
# """
#
# import os
# import asyncio
# from datetime import date
# from typing import Optional, Dict, Any, List, Tuple
#
# from PyQt6 import QtWidgets, uic
# from PyQt6.QtCore import pyqtSignal, QTimer
# from PyQt6.QtWidgets import QMessageBox, QHBoxLayout, QLabel, QComboBox, QCheckBox
#
# from client.core import HierarchyBuilder, EmployeeValidator
#
#
# class EmployeeDialog(QtWidgets.QDialog):
#     """Диалог создания/редактирования сотрудника"""
#
#     employee_created = pyqtSignal(int)
#     employee_updated = pyqtSignal(int)
#
#     def __init__(
#         self,
#         parent_editor=None,
#         employee: Optional[Dict] = None,
#         is_maz: bool = False,
#         profile_manager=None,
#         current_user_rights: str = 'user',
#         current_user_org_id: Optional[int] = None,
#         current_user_div_id: Optional[int] = None,
#         current_user_dept_id: Optional[int] = None,
#         is_organization_head: bool = False,
#         is_division_head: bool = False,
#         is_department_head: bool = False,
#         filter_external_only: bool = False,
#         organization_head_ids: Optional[List[int]] = None
#     ):
#         super().__init__(parent_editor)
#
#         # Сохраняем данные
#         self.employee = employee or {}
#         self.is_maz = is_maz
#         self.profile_manager = profile_manager
#         self.filter_external_only = filter_external_only
#
#         # Данные о пользователе для прав
#         self.current_user_rights = current_user_rights
#         self.current_user_org_id = current_user_org_id
#         self.current_user_div_id = current_user_div_id
#         self.current_user_dept_id = current_user_dept_id
#         self.is_organization_head = is_organization_head
#         self.is_division_head = is_division_head
#         self.is_department_head = is_department_head
#         self.organization_head_ids = organization_head_ids or []
#
#         # Построитель иерархии из модуля core
#         self.hierarchy_builder = HierarchyBuilder()
#
#         # Динамические комбобоксы для иерархии
#         self.hierarchy_combos: List[Tuple[QComboBox, QLabel]] = []
#         self.current_hierarchy_path: List[int] = []
#
#         # Чекбокс руководителя (динамический)
#         self.leader_checkbox: Optional[QCheckBox] = None
#         self.leader_checkbox_layout: Optional[QHBoxLayout] = None
#
#         self._data_loaded = False
#
#         # Загружаем UI
#         self._load_ui()
#
#         # Настраиваем окно
#         self._setup_window()
#
#         # Подключаем сигналы
#         self._connect_signals()
#
#         # Загружаем данные
#         self._load_initial_data()
#
#     def _load_ui(self):
#         """Загружает UI из .ui файла"""
#         current_dir = os.path.dirname(os.path.abspath(__file__))
#         ui_path = os.path.join(
#             current_dir, '..', '..', '..', 'ui', 'system', 'employees', 'employee_dialog.ui'
#         )
#         ui_path = os.path.normpath(ui_path)
#
#         if not os.path.exists(ui_path):
#             raise FileNotFoundError(f"UI file not found: {ui_path}")
#
#         uic.loadUi(ui_path, self)
#
#     def _setup_window(self):
#         """Настраивает заголовок окна"""
#         is_edit = bool(self.employee.get('id'))
#
#         if is_edit:
#             full_name = f"{self.employee.get('last_name', '')} {self.employee.get('first_name', '')}"
#             self.setWindowTitle(f"Редактирование сотрудника - {full_name}")
#             self.titleLabel.setText("Редактирование сотрудника")
#         else:
#             self.setWindowTitle("Новый сотрудник")
#             self.titleLabel.setText("Новый сотрудник")
#
#         self.resize(750, 850)
#
#         # Настройка комбобоксов, не зависящих от данных
#         self._setup_static_comboboxes()
#
#     def _setup_static_comboboxes(self):
#         """Настраивает статические комбобоксы"""
#         # Тип назначения
#         self.assignmentTypeCombo.clear()
#         self.assignmentTypeCombo.addItem("Основное", "primary")
#         self.assignmentTypeCombo.addItem("Совместительство", "part_time")
#         self.assignmentTypeCombo.addItem("Исполняющий обязанности", "acting_director")
#
#         # Права доступа
#         self.rightsCombo.clear()
#         self.rightsCombo.addItem("Пользователь", "user")
#
#         if self.current_user_rights in ['admin', 'superadmin']:
#             self.rightsCombo.addItem("Администратор", "admin")
#             if self.current_user_rights == 'superadmin':
#                 self.rightsCombo.addItem("Суперадминистратор", "superadmin")
#
#         # Скрываем старый чекбокс руководителя (он будет динамическим)
#         self.isLeaderCheckbox.hide()
#
#     def _connect_signals(self):
#         """Подключает сигналы"""
#         self.saveButton.clicked.connect(self.save)
#         self.cancelButton.clicked.connect(self.reject)
#
#     def _load_initial_data(self):
#         """Загружает начальные данные"""
#         if self.profile_manager:
#             try:
#                 loop = asyncio.get_running_loop()
#                 loop.create_task(self._load_data_async())
#             except RuntimeError:
#                 QTimer.singleShot(100, lambda: asyncio.run(self._load_data_async()))
#         else:
#             self._fill_test_data()
#
#     async def _load_data_async(self):
#         """Асинхронная загрузка данных справочников"""
#         try:
#             print("[INFO] Начало загрузки данных...")
#
#             if self.profile_manager:
#                 await self.profile_manager.initialize()
#
#                 # Загружаем организации
#                 orgs = await self.profile_manager.get_all_organizations()
#                 organizations = {org['id']: org['name'] for org in orgs}
#                 print(f"[INFO] Загружено организаций: {len(organizations)}")
#
#                 # Загружаем все подразделения
#                 departments = await self.profile_manager.get_all_departments()
#                 print(f"[INFO] Загружено подразделений: {len(departments)}")
#
#                 # Строим дерево через HierarchyBuilder
#                 self.hierarchy_builder.set_organizations(organizations)
#                 self.hierarchy_builder.build_from_list(departments)
#
#             self._data_loaded = True
#
#             # Обновляем UI в главном потоке
#             self._build_initial_hierarchy()
#
#             # Если редактируем сотрудника, заполняем данные
#             if self.employee:
#                 self._fill_employee_data()
#
#         except Exception as e:
#             print(f"[ERROR] Ошибка загрузки данных: {e}")
#             import traceback
#             traceback.print_exc()
#             self._fill_test_data()
#
#     def _fill_test_data(self):
#         """Заполняет тестовые данные для отладки"""
#         print("[INFO] Используются тестовые данные")
#
#         test_organizations = {
#             1: "ОАО МАЗ",
#             2: "ООО Тестовая организация"
#         }
#
#         test_departments = [
#             {'id': 1, 'name': 'Управление информационных технологий', 'parent_id': None, 'organization_id': 1, 'level': 1},
#             {'id': 2, 'name': 'Отдел разработки', 'parent_id': 1, 'organization_id': 1, 'level': 2},
#             {'id': 3, 'name': 'Отдел тестирования', 'parent_id': 1, 'organization_id': 1, 'level': 2},
#             {'id': 4, 'name': 'Группа бэкенда', 'parent_id': 2, 'organization_id': 1, 'level': 3},
#             {'id': 5, 'name': 'Управление продаж', 'parent_id': None, 'organization_id': 2, 'level': 1},
#             {'id': 6, 'name': 'Отдел прямых продаж', 'parent_id': 5, 'organization_id': 2, 'level': 2},
#         ]
#
#         self.hierarchy_builder.set_organizations(test_organizations)
#         self.hierarchy_builder.build_from_list(test_departments)
#
#         self._data_loaded = True
#         self._build_initial_hierarchy()
#
#         if self.employee:
#             self._fill_employee_data()
#
#     def _build_initial_hierarchy(self):
#         """Строит начальную иерархию: Организация -> Руководитель"""
#         # Очищаем существующую иерархию
#         self._clear_hierarchy()
#
#         # Добавляем первый уровень - Организация
#         exclude_ids = [1] if self.filter_external_only else None
#         org_items = self.hierarchy_builder.get_organizations_for_select(exclude_ids)
#
#         self._add_hierarchy_level(0, None, "Организация *:", org_items)
#
#         # Добавляем чекбокс "Руководитель" сразу после организации
#         self._add_leader_checkbox()
#
#         # Если редактируем сотрудника, устанавливаем выбранную организацию
#         if self.employee and self.employee.get('organization_id'):
#             org_id = self.employee.get('organization_id')
#             if self.hierarchy_combos:
#                 combo = self.hierarchy_combos[0][0]
#                 index = combo.findData(org_id)
#                 if index >= 0:
#                     combo.setCurrentIndex(index)
#
#     def _add_leader_checkbox(self):
#         """Добавляет чекбокс руководителя после организации"""
#         # Создаем layout для чекбокса
#         row_layout = QHBoxLayout()
#         row_layout.setSpacing(10)
#
#         # Пустая метка для выравнивания
#         label = QLabel("")
#         label.setMinimumSize(120, 0)
#
#         # Создаем чекбокс
#         self.leader_checkbox = QCheckBox("Является руководителем организации")
#         self.leader_checkbox.setStyleSheet("spacing: 8px; color: #1B232A;")
#         self.leader_checkbox.setEnabled(False)  # Изначально неактивен (нет выбранной организации)
#         self.leader_checkbox.toggled.connect(self._on_leader_toggled)
#
#         # Добавляем в layout
#         row_layout.addWidget(label)
#         row_layout.addWidget(self.leader_checkbox)
#
#         # Сохраняем layout для последующего удаления/обновления
#         self.leader_checkbox_layout = row_layout
#
#         # Добавляем в основной layout
#         self.hierarchyLayout.addLayout(row_layout)
#
#     def _clear_hierarchy(self):
#         """Очищает все динамические элементы иерархии"""
#         # Удаляем все виджеты из hierarchyLayout
#         while self.hierarchyLayout.count():
#             item = self.hierarchyLayout.takeAt(0)
#             if item.layout():
#                 # Удаляем все элементы из вложенного layout
#                 while item.layout().count():
#                     sub_item = item.layout().takeAt(0)
#                     if sub_item.widget():
#                         sub_item.widget().deleteLater()
#                 item.layout().deleteLater()
#
#         self.hierarchy_combos = []
#         self.current_hierarchy_path = []
#         self.leader_checkbox = None
#         self.leader_checkbox_layout = None
#
#     def _add_hierarchy_level(self, level: int, parent_id: Optional[int],
#                              label_text: str, items: List[Tuple[int, str]]):
#         """
#         Добавляет уровень иерархии
#
#         Args:
#             level: Уровень вложенности (0 - организация, 1 - подразделение, ...)
#             parent_id: ID родительского элемента
#             label_text: Текст метки
#             items: Список [(id, name), ...] для комбобокса
#         """
#         # Создаем layout для строки
#         row_layout = QHBoxLayout()
#         row_layout.setSpacing(10)
#
#         # Создаем метку
#         label = QLabel(label_text)
#         label.setMinimumSize(120, 0)
#         label.setStyleSheet("color: #1B232A; font-weight: 500;")
#
#         # Создаем комбобокс
#         combo = QComboBox()
#         combo.setStyleSheet(
#             "border: 1px solid #dee2e6; border-radius: 6px; padding: 5px; background-color: white;"
#         )
#         combo.addItem("Не выбрано", None)
#
#         for item_id, item_name in items:
#             combo.addItem(item_name, item_id)
#
#         # Подключаем сигнал изменения
#         combo.currentIndexChanged.connect(
#             lambda idx, lvl=level, cb=combo: self._on_hierarchy_changed(lvl, cb)
#         )
#
#         # Добавляем в layout
#         row_layout.addWidget(label)
#         row_layout.addWidget(combo)
#
#         # Определяем позицию для вставки
#         if level == 0:
#             self.hierarchyLayout.insertLayout(0, row_layout)
#             self.hierarchy_combos.insert(0, (combo, label))
#         else:
#             checkbox_position = self.hierarchyLayout.indexOf(self.leader_checkbox_layout)
#             if checkbox_position >= 0:
#                 self.hierarchyLayout.insertLayout(checkbox_position, row_layout)
#                 self.hierarchy_combos.insert(level, (combo, label))
#             else:
#                 self.hierarchyLayout.addLayout(row_layout)
#                 self.hierarchy_combos.append((combo, label))
#
#         return combo, label
#
#     def _on_hierarchy_changed(self, level: int, combo: QComboBox):
#         """
#         Обработчик изменения значения в иерархическом комбобоксе
#
#         Args:
#             level: Уровень, который изменился
#             combo: Комбобокс, который изменился
#         """
#         # Блокируем сигналы чекбокса, чтобы избежать рекурсии
#         if self.leader_checkbox:
#             self.leader_checkbox.blockSignals(True)
#
#         # Получаем выбранное значение
#         selected_id = combo.currentData()
#
#         # Обновляем путь
#         self.current_hierarchy_path = self.current_hierarchy_path[:level]
#         if selected_id:
#             self.current_hierarchy_path.append(selected_id)
#
#         # Удаляем все уровни после текущего
#         self._remove_levels_after(level)
#
#         # Сбрасываем чекбокс руководителя при изменении структуры
#         if self.leader_checkbox:
#             self.leader_checkbox.setChecked(False)
#
#         # Если что-то выбрано и это не "Не выбрано"
#         if selected_id:
#             children = self.hierarchy_builder.get_children(selected_id)
#             if children:
#                 next_level = level + 1
#                 level_name = self.hierarchy_builder.get_level_name(next_level)
#                 self._add_hierarchy_level(next_level, selected_id, f"{level_name}:", children)
#
#         # Обновляем чекбокс руководителя
#         self._update_leader_checkbox()
#
#         # Разблокируем сигналы чекбокса
#         if self.leader_checkbox:
#             self.leader_checkbox.blockSignals(False)
#
#     def _on_leader_toggled(self, checked: bool):
#         """Обработчик переключения чекбокса руководителя"""
#         if checked:
#             if len(self.current_hierarchy_path) == 0:
#                 self.leader_checkbox.setChecked(False)
#                 QMessageBox.warning(
#                     self, "Предупреждение",
#                     "Для назначения руководителем необходимо выбрать организацию"
#                 )
#                 return
#
#             if len(self.hierarchy_combos) > 1:
#                 last_combo = self.hierarchy_combos[-1][0]
#                 last_selected = last_combo.currentData()
#                 if last_selected is None:
#                     self._hide_last_level()
#         else:
#             self._show_last_level()
#
#         self._update_leader_checkbox()
#
#     def _update_leader_checkbox(self):
#         """Обновляет состояние и текст чекбокса руководителя"""
#         if not self.leader_checkbox:
#             return
#
#         has_organization = len(self.current_hierarchy_path) > 0
#         self.leader_checkbox.setEnabled(has_organization)
#
#         if not has_organization:
#             self.leader_checkbox.setChecked(False)
#             self.leader_checkbox.setText("Является руководителем организации")
#             return
#
#         # Определяем уровень
#         if len(self.hierarchy_combos) > 1:
#             last_combo = self.hierarchy_combos[-1][0]
#             last_selected = last_combo.currentData()
#
#             if last_selected:
#                 last_level = len(self.hierarchy_combos) - 1
#                 level_name = self.hierarchy_builder.get_level_name(last_level).lower()
#                 self.leader_checkbox.setText(f"Является руководителем {level_name}")
#             elif len(self.hierarchy_combos) > 2:
#                 prev_level = len(self.hierarchy_combos) - 2
#                 level_name = self.hierarchy_builder.get_level_name(prev_level).lower()
#                 self.leader_checkbox.setText(f"Является руководителем {level_name}")
#             else:
#                 self.leader_checkbox.setText("Является руководителем организации")
#         else:
#             self.leader_checkbox.setText("Является руководителем организации")
#
#     def _hide_last_level(self):
#         """Скрывает последний уровень иерархии при отметке руководителя"""
#         if len(self.hierarchy_combos) <= 1:
#             return
#
#         last_combo, _ = self.hierarchy_combos[-1]
#
#         for i in range(self.hierarchyLayout.count()):
#             item = self.hierarchyLayout.itemAt(i)
#             if item and item.layout():
#                 layout = item.layout()
#                 for j in range(layout.count()):
#                     widget_item = layout.itemAt(j)
#                     if widget_item and widget_item.widget() == last_combo:
#                         for k in range(layout.count()):
#                             hide_item = layout.itemAt(k)
#                             if hide_item and hide_item.widget():
#                                 hide_item.widget().hide()
#                         return
#
#     def _show_last_level(self):
#         """Показывает последний уровень иерархии при снятии отметки руководителя"""
#         if len(self.hierarchy_combos) <= 1:
#             return
#
#         last_combo, _ = self.hierarchy_combos[-1]
#
#         for i in range(self.hierarchyLayout.count()):
#             item = self.hierarchyLayout.itemAt(i)
#             if item and item.layout():
#                 layout = item.layout()
#                 for j in range(layout.count()):
#                     widget_item = layout.itemAt(j)
#                     if widget_item and widget_item.widget() == last_combo:
#                         for k in range(layout.count()):
#                             show_item = layout.itemAt(k)
#                             if show_item and show_item.widget():
#                                 show_item.widget().show()
#                         return
#
#     def _remove_levels_after(self, level: int):
#         """Удаляет все уровни иерархии после указанного"""
#         while len(self.hierarchy_combos) > level + 1:
#             last_combo, _ = self.hierarchy_combos[-1]
#
#             for i in range(self.hierarchyLayout.count()):
#                 item = self.hierarchyLayout.itemAt(i)
#                 if item and item.layout():
#                     layout = item.layout()
#                     for j in range(layout.count()):
#                         widget_item = layout.itemAt(j)
#                         if widget_item and widget_item.widget() == last_combo:
#                             while layout.count():
#                                 sub_item = layout.takeAt(0)
#                                 if sub_item.widget():
#                                     sub_item.widget().deleteLater()
#                             self.hierarchyLayout.removeItem(item)
#                             layout.deleteLater()
#                             break
#                     else:
#                         continue
#                     break
#
#             self.hierarchy_combos.pop()
#
#     def _get_current_hierarchy_path(self) -> List[int]:
#         """Возвращает текущий путь иерархии [org_id, dep1_id, dep2_id, ...]"""
#         path = []
#         for combo, _ in self.hierarchy_combos:
#             selected_id = combo.currentData()
#             if selected_id:
#                 path.append(selected_id)
#             else:
#                 break
#         return path
#
#     def get_data(self) -> Dict[str, Any]:
#         """Возвращает данные из формы"""
#         rights_index = self.rightsCombo.currentIndex()
#         rights = self.rightsCombo.itemData(rights_index) or 'user'
#
#         assignment_index = self.assignmentTypeCombo.currentIndex()
#         assignment_kind = self.assignmentTypeCombo.itemData(assignment_index) or 'primary'
#
#         # Получаем путь иерархии
#         hierarchy_path = self._get_current_hierarchy_path()
#
#         # Определяем department_id
#         is_leader = self.leader_checkbox.isChecked() if self.leader_checkbox else False
#
#         if is_leader:
#             if len(self.hierarchy_combos) > 1:
#                 last_combo = self.hierarchy_combos[-1][0]
#                 last_selected = last_combo.currentData()
#                 if last_selected:
#                     department_id = last_selected
#                 elif len(self.hierarchy_combos) > 2:
#                     prev_combo = self.hierarchy_combos[-2][0]
#                     department_id = prev_combo.currentData()
#                 else:
#                     department_id = None
#             else:
#                 department_id = None
#         else:
#             department_id = hierarchy_path[-1] if hierarchy_path else None
#
#         organization_id = hierarchy_path[0] if hierarchy_path else None
#
#         chat_id_text = self.chatIdEdit.text().strip()
#         chat_id = int(chat_id_text) if chat_id_text and chat_id_text.isdigit() else None
#
#         data = {
#             'last_name': self.lastNameEdit.text().strip(),
#             'first_name': self.firstNameEdit.text().strip(),
#             'patronymic': self.patronymicEdit.text().strip(),
#             'phone_number': self.phoneEdit.text().strip(),
#             'work_number': self.workPhoneEdit.text().strip(),
#             'email': self.emailEdit.text().strip(),
#             'birth_date': self.birthDateEdit.date().toPyDate(),
#             'chat_id': chat_id,
#             'organization_id': organization_id,
#             'department_id': department_id,
#             'hierarchy_path': hierarchy_path,
#             'position_name': self.positionEdit.text().strip(),
#             'assignment_kind': assignment_kind,
#             'is_leader': is_leader,
#             'rights': rights,
#             'is_active': True
#         }
#
#         if self.employee.get('id'):
#             data['id'] = self.employee['id']
#
#         return data
#
#     def _fill_employee_data(self):
#         """Заполняет поля данными сотрудника"""
#         if not self.employee or not self._data_loaded:
#             return
#
#         print("[INFO] Заполнение данных сотрудника...")
#
#         # Личная информация
#         self.lastNameEdit.setText(self.employee.get('last_name', ''))
#         self.firstNameEdit.setText(self.employee.get('first_name', ''))
#         self.patronymicEdit.setText(self.employee.get('patronymic', ''))
#         self.serviceNumberEdit.setText(self.employee.get('service_number', ''))
#
#         # Дата рождения
#         birth_date = self.employee.get('birth_date')
#         if birth_date:
#             if isinstance(birth_date, str):
#                 from datetime import datetime
#                 try:
#                     birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
#                 except ValueError:
#                     birth_date = date(1980, 1, 1)
#             self.birthDateEdit.setDate(birth_date)
#         else:
#             self.birthDateEdit.setDate(date(1980, 1, 1))
#
#         # Контакты
#         self.phoneEdit.setText(self.employee.get('phone_number', ''))
#         self.workPhoneEdit.setText(self.employee.get('work_number', ''))
#         self.emailEdit.setText(self.employee.get('email', ''))
#         chat_id = self.employee.get('chat_id')
#         self.chatIdEdit.setText(str(chat_id) if chat_id else '')
#
#         # Рабочая информация
#         self.positionEdit.setText(self.employee.get('position_name', ''))
#
#         # Тип назначения
#         assignment_type = self.employee.get('assignment_kind', 'primary')
#         for i in range(self.assignmentTypeCombo.count()):
#             if self.assignmentTypeCombo.itemData(i) == assignment_type:
#                 self.assignmentTypeCombo.setCurrentIndex(i)
#                 break
#
#         # Права
#         rights = self.employee.get('rights', 'user')
#         for i in range(self.rightsCombo.count()):
#             if self.rightsCombo.itemData(i) == rights:
#                 self.rightsCombo.setCurrentIndex(i)
#                 break
#
#         # Иерархия и руководитель
#         is_leader = self.employee.get('is_leader', False)
#         hierarchy_path = self.employee.get('hierarchy_path', [])
#
#         if hierarchy_path:
#             for level, item_id in enumerate(hierarchy_path):
#                 if level < len(self.hierarchy_combos):
#                     combo = self.hierarchy_combos[level][0]
#                     index = combo.findData(item_id)
#                     if index >= 0:
#                         combo.setCurrentIndex(index)
#
#             if is_leader and self.leader_checkbox:
#                 self.leader_checkbox.setChecked(True)
#
#         elif self.employee.get('organization_id'):
#             # Старый формат данных
#             org_id = self.employee.get('organization_id')
#             dept_id = self.employee.get('department_id')
#
#             if self.hierarchy_combos:
#                 combo = self.hierarchy_combos[0][0]
#                 index = combo.findData(org_id)
#                 if index >= 0:
#                     combo.setCurrentIndex(index)
#
#             if dept_id:
#                 QTimer.singleShot(500, lambda: self._set_old_format_data(dept_id, is_leader))
#
#     def _set_old_format_data(self, dept_id: int, is_leader: bool):
#         """Устанавливает данные из старого формата"""
#         path = self.hierarchy_builder.get_path_to_root(dept_id)
#
#         if path:
#             for level, item_id in enumerate(path[1:], start=1):
#                 if level < len(self.hierarchy_combos):
#                     combo = self.hierarchy_combos[level][0]
#                     index = combo.findData(item_id)
#                     if index >= 0:
#                         combo.setCurrentIndex(index)
#
#             if is_leader and self.leader_checkbox:
#                 self.leader_checkbox.setChecked(True)
#
#     def validate(self) -> List[str]:
#         """Валидация данных"""
#         data = self.get_data()
#         is_edit = bool(self.employee.get('id'))
#         validator = EmployeeValidator(is_edit=is_edit)
#         return validator.validate(data)
#
#     def save(self):
#         """Сохраняет данные"""
#         errors = self.validate()
#         if errors:
#             QMessageBox.warning(self, "Ошибка валидации", "\n".join(errors))
#             return
#
#         data = self.get_data()
#         is_edit = bool(self.employee.get('id'))
#
#         if is_edit:
#             self._start_async_update(data)
#         else:
#             self._start_async_create(data)
#
#     def _start_async_create(self, data: Dict[str, Any]):
#         """Запускает асинхронное создание сотрудника"""
#         if self.profile_manager:
#             try:
#                 loop = asyncio.get_running_loop()
#                 loop.create_task(self._create_employee(data))
#             except RuntimeError:
#                 asyncio.run(self._create_employee(data))
#         else:
#             print(f"[TEST] Создание сотрудника: {data}")
#             self.accept()
#
#     def _start_async_update(self, data: Dict[str, Any]):
#         """Запускает асинхронное обновление сотрудника"""
#         if self.profile_manager:
#             try:
#                 loop = asyncio.get_running_loop()
#                 loop.create_task(self._update_employee(data))
#             except RuntimeError:
#                 asyncio.run(self._update_employee(data))
#         else:
#             print(f"[TEST] Обновление сотрудника: {data}")
#             self.accept()
#
#     async def _create_employee(self, data: Dict[str, Any]):
#         """Асинхронное создание сотрудника"""
#         try:
#             from datetime import datetime
#             data['service_number'] = f"EMP_{datetime.now().strftime('%Y%m%d%H%M%S')}"
#
#             if self.profile_manager:
#                 employee_id = await self.profile_manager.add_employee(data)
#                 if employee_id:
#                     self.employee_created.emit(employee_id)
#                     self.accept()
#                 else:
#                     self._show_error("Не удалось создать сотрудника")
#             else:
#                 self.accept()
#
#         except Exception as e:
#             print(f"[ERROR] Ошибка создания сотрудника: {e}")
#             self._show_error(f"Ошибка: {str(e)}")
#
#     async def _update_employee(self, data: Dict[str, Any]):
#         """Асинхронное обновление сотрудника"""
#         try:
#             employee_id = self.employee['id']
#
#             if self.profile_manager:
#                 success = await self.profile_manager.update_employee(employee_id, data)
#                 if success:
#                     self.employee_updated.emit(employee_id)
#                     self.accept()
#                 else:
#                     self._show_error("Не удалось обновить данные сотрудника")
#             else:
#                 self.accept()
#
#         except Exception as e:
#             print(f"[ERROR] Ошибка обновления сотрудника: {e}")
#             self._show_error(f"Ошибка: {str(e)}")
#
#     def _show_error(self, message: str):
#         """Показывает ошибку"""
#         QMessageBox.critical(self, "Ошибка", message)
#
#     def closeEvent(self, event):
#         """Обработчик закрытия окна"""
#         super().closeEvent(event)
#
#
# # Тестовый запуск
# if __name__ == '__main__':
#     import sys
#
#     app = QtWidgets.QApplication(sys.argv)
#
#     print("=" * 50)
#     print("Тест: Создание нового сотрудника")
#     print("=" * 50)
#
#     dialog = EmployeeDialog(
#         parent_editor=None,
#         employee=None,
#         current_user_rights='admin'
#     )
#     dialog.show()
#
#     sys.exit(app.exec())

