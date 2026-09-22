import os
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import QDialog, QApplication, QTreeWidgetItem
from PyQt6.QtCore import pyqtSignal, Qt

from client.core.org_structure.hierarchy_builder import HierarchyBuilder
from client.core.org_structure.selection_manager import SelectionManager
from client.core.org_structure.tree_builder import TreeBuilder
from client.core.themes import apply_theme_to_widget
from client.windows.documents.table.create.employee_selection import EmployeeSelection


class EmployeeSelectionDialog(QDialog):
    """
    Диалог выбора получателей с древовидной структурой.
    Поддерживает выбор организаций, отделов и сотрудников.
    """
    selection_confirmed = pyqtSignal(list)

    def __init__(self,
                 organizations: List[Dict[str, Any]],
                 departments: List[Dict[str, Any]],
                 employees: List[Dict[str, Any]],
                 preselected_ids: Optional[List[int]] = None,
                 parent=None,
                 title: str = "Выбор получателей",
                 instruction: str = "Выберите организации, отделы или сотрудников:"):
        super().__init__(parent)

        # Флаг для предотвращения рекурсии
        self._updating = False

        # Инициализация данных
        self._init_data(organizations, departments, employees, preselected_ids)

        # Инициализация UI
        self._init_ui(title, instruction)

        # Заполнение дерева
        self._populate_tree()

        # Подключение сигналов
        self._connect_signals()

        # Обновление информации
        self._update_selection_info()

    def _init_data(self, organizations, departments, employees, preselected_ids):
        """Инициализация данных"""
        self.builder = HierarchyBuilder(organizations, departments, employees)
        self.org_hierarchy = self.builder.build()

        self.selection_manager = SelectionManager(
            self.builder.organizations,
            self.builder.departments,
            self.builder.employees
        )
        if preselected_ids:
            self.selection_manager.set_selected(preselected_ids)

        self.tree_builder = TreeBuilder(self.org_hierarchy, self.selection_manager)

    def _init_ui(self, title: str, instruction: str):
        """Инициализация UI"""
        ui_path = EmployeeSelection.get_ui_path()

        EmployeeSelection.load_ui(self, ui_path)
        apply_theme_to_widget(self)
        # Настройка заголовков
        if hasattr(self, 'titleLabel'):
            self.titleLabel.setText(title)
        if hasattr(self, 'instructionLabel'):
            self.instructionLabel.setText(instruction)

        # Настройка дерева
        if hasattr(self, 'treeWidget'):
            self.treeWidget.setHeaderLabel("Структура организации")
            self.treeWidget.setIndentation(20)
            self.treeWidget.setItemsExpandable(True)

        # Применение стилей с чекбоксами
        base_dir = self._get_root_dir()
        EmployeeSelection.apply_checkbox_styles(self, base_dir)

    def _get_root_dir(self) -> str:
        """Определяет корневую директорию проекта"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = base_dir
        for _ in range(4):
            root_dir = os.path.dirname(root_dir)
        return root_dir

    def _connect_signals(self):
        """Подключение сигналов"""
        if hasattr(self, 'searchEdit'):
            self.searchEdit.textChanged.connect(self._on_search)
        if hasattr(self, 'treeWidget'):
            self.treeWidget.itemChanged.connect(self._on_tree_item_changed)
        if hasattr(self, 'selectButton'):
            self.selectButton.clicked.connect(self._on_select)
        if hasattr(self, 'cancelButton'):
            self.cancelButton.clicked.connect(self.reject)

    def _on_tree_item_changed(self, item, column):
        """
        Обработка изменения состояния чекбокса.
        Обновляет всю иерархию.
        """
        if self._updating:
            return

        # Проверяем, есть ли чекбокс у элемента
        if not (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
            return

        # Получаем новое состояние
        new_state = item.checkState(column)
        is_checked = (new_state == Qt.CheckState.Checked)

        # Получаем данные элемента
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        node_id = data.get('id')
        node_type = data.get('type')

        if node_id is None or node_id < 0 or node_type is None:
            return

        print(f"[DEBUG] Изменение элемента: id={node_id}, type={node_type}, checked={is_checked}")
        print(f"[DEBUG] До изменения: {self.selection_manager.get_selection_stats()}")

        # Устанавливаем флаг обновления
        self._updating = True

        try:
            # 1. Обновляем текущий элемент
            self.selection_manager.toggle(node_id, is_checked, node_type)

            # 2. Обновляем всех потомков
            all_descendants = self._get_all_descendants(item)
            print(f"[DEBUG] Найдено потомков: {len(all_descendants)}")

            # Собираем уникальные (type, id) потомков
            descendant_items = set()
            for child_item in all_descendants:
                child_data = child_item.data(0, Qt.ItemDataRole.UserRole)
                if child_data and child_data.get('id') and child_data.get('id') > 0:
                    child_type = child_data.get('type')
                    if child_type is not None:
                        descendant_items.add((child_type, child_data['id']))

            print(f"[DEBUG] Уникальных потомков: {len(descendant_items)}")

            # Обновляем SelectionManager для всех потомков
            for child_type, child_id in descendant_items:
                self.selection_manager.toggle(child_id, is_checked, child_type)
                print(f"[DEBUG]   Потомок: id={child_id}, type={child_type}, checked={is_checked}")

            # 3. Обновляем чекбоксы всех потомков в дереве (без генерации сигналов)
            for child_item in all_descendants:
                child_data = child_item.data(0, Qt.ItemDataRole.UserRole)
                if child_data and child_data.get('id') and child_data.get('id') > 0:
                    child_item.setCheckState(0, Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked)

            # 4. Обновляем всех предков (без изменения SelectionManager для предков)
            if item.parent():
                self._update_parent_checks_only(item.parent())

            # 5. Обновляем информацию
            self._update_selection_info()

            print(f"[DEBUG] После изменения: {self.selection_manager.get_selection_stats()}")

        finally:
            self._updating = False

    def _update_parent_checks_only(self, item):
        """
        Обновляет состояние родительских чекбоксов на основе детей.
        НЕ изменяет SelectionManager для родителей.
        """
        if not (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
            return

        checked_count = 0
        total_count = 0

        # Считаем состояние всех детей
        for i in range(item.childCount()):
            child = item.child(i)
            if child.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                total_count += 1
                if child.checkState(0) == Qt.CheckState.Checked:
                    checked_count += 1

        if total_count == 0:
            return

        # Определяем новое состояние для родителя
        if checked_count == total_count:
            new_state = Qt.CheckState.Checked
        else:
            new_state = Qt.CheckState.Unchecked

        # Устанавливаем новое состояние (без сигналов, т.к. мы в _updating)
        item.setCheckState(0, new_state)

        # Рекурсивно обновляем вышестоящих родителей
        if item.parent():
            self._update_parent_checks_only(item.parent())

    def _update_parent_checks(self, item):
        """
        [УСТАРЕЛ] Используйте _update_parent_checks_only
        """
        pass


    def _get_all_descendants(self, item) -> List[QTreeWidgetItem]:
        """
        Возвращает список всех потомков элемента (рекурсивно).
        """
        descendants = []
        for i in range(item.childCount()):
            child = item.child(i)
            descendants.append(child)
            descendants.extend(self._get_all_descendants(child))
        return descendants

    def _populate_tree(self, filter_text: str = ""):
        """Заполняет дерево"""
        if not hasattr(self, 'treeWidget'):
            return

        # Блокируем сигналы при заполнении
        self.treeWidget.blockSignals(True)
        try:
            self.treeWidget.clear()

            items = self.tree_builder.build_tree(filter_text)
            print(f"[DEBUG] Построено элементов дерева: {len(items)}")

            # Добавляем элементы в дерево
            for item in items:
                self.treeWidget.addTopLevelItem(item)
                # Устанавливаем состояние чекбокса для корневых элементов
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if data and data.get('id') and data.get('id') > 0:
                    node_id = data['id']
                    if self.selection_manager.is_selected(node_id):
                        item.setCheckState(0, Qt.CheckState.Checked)
                    else:
                        item.setCheckState(0, Qt.CheckState.Unchecked)

                    # Рекурсивно устанавливаем состояние для всех детей
                    self._set_checkboxes_recursive(item)

                if data:
                    print(
                        f"[DEBUG] Корневой элемент: id={data.get('id')}, type={data.get('type')}, детей={item.childCount()}")

            # Дополнительная синхронизация после заполнения
            self._sync_all_checkboxes()

        finally:
            self.treeWidget.blockSignals(False)

    def _set_checkboxes_recursive(self, item):
        """Рекурсивно устанавливает состояние чекбоксов для всех потомков"""
        for i in range(item.childCount()):
            child = item.child(i)
            child_data = child.data(0, Qt.ItemDataRole.UserRole)
            if child_data and child_data.get('id') and child_data.get('id') > 0:
                node_id = child_data['id']
                if self.selection_manager.is_selected(node_id):
                    child.setCheckState(0, Qt.CheckState.Checked)
                else:
                    child.setCheckState(0, Qt.CheckState.Unchecked)
            # Рекурсивно обрабатываем детей этого элемента
            self._set_checkboxes_recursive(child)

    def _sync_all_checkboxes(self):
        """Полная синхронизация всех чекбоксов с SelectionManager"""

        def sync_item(item):
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get('id') and data.get('id') > 0:
                node_id = data['id']
                is_selected = self.selection_manager.is_selected(node_id)
                item.setCheckState(0, Qt.CheckState.Checked if is_selected else Qt.CheckState.Unchecked)

            # Рекурсивно синхронизируем детей
            for i in range(item.childCount()):
                sync_item(item.child(i))

        # Начинаем синхронизацию с корневых элементов
        for i in range(self.treeWidget.topLevelItemCount()):
            sync_item(self.treeWidget.topLevelItem(i))

    def _sync_checkboxes_from_selection(self):
        """
        Синхронизирует состояние чекбоксов с SelectionManager.
        Проходит по всем элементам дерева и устанавливает правильное состояние.
        """

        def sync_item(item):
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get('id') and data.get('id') > 0:
                node_id = data['id']
                node_type = data.get('type')
                # Проверяем, выбран ли этот элемент в SelectionManager
                is_selected = self.selection_manager.is_selected(node_id)
                if is_selected:
                    item.setCheckState(0, Qt.CheckState.Checked)
                    print(f"[DEBUG] Синхронизация: id={node_id}, type={node_type} -> Checked")
                else:
                    item.setCheckState(0, Qt.CheckState.Unchecked)
                    print(f"[DEBUG] Синхронизация: id={node_id}, type={node_type} -> Unchecked")

            # Рекурсивно синхронизируем детей
            for i in range(item.childCount()):
                sync_item(item.child(i))

        # Начинаем синхронизацию с корневых элементов
        for i in range(self.treeWidget.topLevelItemCount()):
            sync_item(self.treeWidget.topLevelItem(i))

        # Обновляем информацию после синхронизации
        self._update_selection_info()

    def _on_search(self, text: str):
        """Обработка поиска"""
        self._populate_tree(text)

    def _update_selection_info(self):
        """Обновляет информацию о выбранных элементах"""
        if not hasattr(self, 'selectionInfoLabel'):
            return

        # Получаем выбранные элементы с типами
        selected_items = self.selection_manager.get_selected_items()

        # Считаем организации, отделы и сотрудников отдельно
        org_count = 0
        dept_count = 0
        emp_count = 0

        for type_id, node_id in selected_items:
            if type_id == 1:  # Организация
                org_count += 1
            elif type_id == 2:  # Отдел
                dept_count += 1
            elif type_id == 3:  # Сотрудник
                emp_count += 1

        total = len(selected_items)

        if total == 0:
            self.selectionInfoLabel.setText("Выбрано: 0 элементов")
        else:
            # Формируем строку с учетом всех типов
            parts = [f"Выбрано: {total} элементов"]
            if org_count > 0:
                parts.append(f"организаций: {org_count}")
            if dept_count > 0:
                parts.append(f"отделов: {dept_count}")
            if emp_count > 0:
                parts.append(f"сотрудников: {emp_count}")

            self.selectionInfoLabel.setText(" (".join(parts) + ")")
            print(f"[DEBUG] Статистика: всего={total}, орг={org_count}, отд={dept_count}, сотр={emp_count}")

    def _get_node_type(self, node_id: int) -> Optional[int]:
        """Получает тип узла по ID"""
        # Используем тот же метод, что и в SelectionManager
        if node_id in self.builder.organizations:
            return 1
        if node_id in self.builder.departments:
            return 2
        if node_id in self.builder.employees:
            return 3
        return None

    def _on_select(self):
        """Подтверждение выбора"""
        selected_ids = self.selection_manager.get_selected_ids()
        print(f"[DEBUG] Выбранные ID: {selected_ids}")
        self.selection_confirmed.emit(selected_ids)
        self.accept()

    # Public методы
    def get_selected_ids(self) -> List[int]:
        return self.selection_manager.get_selected_ids()

    def get_selected_organizations(self) -> List[Dict]:
        return self.selection_manager.get_selected_organizations()

    def get_selected_departments(self) -> List[Dict]:
        return self.selection_manager.get_selected_departments()

    def get_selected_employees(self) -> List[Dict]:
        return self.selection_manager.get_selected_employees()