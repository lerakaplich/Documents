import os
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import QDialog, QApplication
from PyQt6.QtCore import pyqtSignal, Qt

from client.core.org_structure.hierarchy_builder import HierarchyBuilder
from client.core.org_structure.selection_manager import SelectionManager
from client.core.org_structure.tree_builder import TreeBuilder
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
            # МЕНЯЕМ: itemChanged на itemClicked
            self.treeWidget.itemClicked.connect(self._on_tree_item_clicked)  # НОВЫЙ МЕТОД
            # self.treeWidget.itemChanged.connect(self._on_tree_item_changed)  # УДАЛЯЕМ
        if hasattr(self, 'selectButton'):
            self.selectButton.clicked.connect(self._on_select)
        if hasattr(self, 'cancelButton'):
            self.cancelButton.clicked.connect(self.reject)

    def _on_tree_item_clicked(self, item, column):
        """
        НОВЫЙ МЕТОД: Обработка клика по элементу (как у тегов)
        Клик по ЛЮБОЙ части строки переключает чекбокс
        """
        # Проверяем, есть ли чекбокс у элемента
        if not (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
            return

        # Получаем текущее состояние чекбокса
        current_state = item.checkState(column)

        # Определяем новое состояние
        if current_state == Qt.CheckState.Checked:
            new_state = Qt.CheckState.Unchecked
        elif current_state == Qt.CheckState.Unchecked:
            new_state = Qt.CheckState.Checked
        else:  # PartiallyChecked
            new_state = Qt.CheckState.Checked  # Или оставляем как есть

        # Блокируем сигналы чтобы избежать рекурсии
        self.treeWidget.blockSignals(True)

        # Устанавливаем новое состояние
        item.setCheckState(column, new_state)

        # Разблокируем сигналы
        self.treeWidget.blockSignals(False)

        # Получаем данные элемента
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        node_id = data.get('id')
        if node_id is None or node_id < 0:
            return

        # Обновляем выделение
        is_checked = (new_state == Qt.CheckState.Checked)
        self.selection_manager.toggle(node_id, is_checked)

        # Обновляем дочерние элементы
        self._update_children_checks(item, is_checked)

        # Обновляем родительские элементы
        if item.parent():
            self._update_parent_check(item.parent())

        # Обновляем информацию
        self._update_selection_info()

        # Принудительно обновляем виджет
        self.treeWidget.viewport().update()

    # МОЖНО УДАЛИТЬ старый метод _on_tree_item_changed, либо оставить для совместимости
    def _on_tree_item_changed(self, item, column):
        """СТАРЫЙ МЕТОД - больше не используется, но можно оставить"""
        pass

    def _populate_tree(self, filter_text: str = ""):
        """Заполняет дерево"""
        if not hasattr(self, 'treeWidget'):
            return

        self.treeWidget.blockSignals(True)
        self.treeWidget.clear()

        items = self.tree_builder.build_tree(filter_text)
        for item in items:
            self.treeWidget.addTopLevelItem(item)

        self.treeWidget.blockSignals(False)

    def _on_search(self, text: str):
        """Обработка поиска"""
        self._populate_tree(text)

    def _update_children_checks(self, item, checked: bool):
        """Обновляет чекбоксы дочерних элементов"""
        for i in range(item.childCount()):
            child = item.child(i)
            if child.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                child.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
                data = child.data(0, Qt.ItemDataRole.UserRole)
                if data and data.get('id') and data.get('id') > 0:
                    self.selection_manager.toggle(data['id'], checked)
            self._update_children_checks(child, checked)

    def _update_parent_check(self, item):
        """Обновляет состояние родительского чекбокса"""
        if not (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
            return

        checked_count = 0
        total_count = 0

        for i in range(item.childCount()):
            child = item.child(i)
            if child.flags() & Qt.ItemFlag.ItemIsUserCheckable:
                total_count += 1
                if child.checkState(0) == Qt.CheckState.Checked:
                    checked_count += 1

        if total_count == 0:
            return

        if checked_count == total_count:
            item.setCheckState(0, Qt.CheckState.Checked)
        elif checked_count == 0:
            item.setCheckState(0, Qt.CheckState.Unchecked)
        else:
            item.setCheckState(0, Qt.CheckState.PartiallyChecked)

    def _update_selection_info(self):
        """Обновляет информацию о выбранных элементах"""
        if not hasattr(self, 'selectionInfoLabel'):
            return

        stats = self.selection_manager.get_selection_stats()
        if stats['total'] == 0:
            self.selectionInfoLabel.setText("Выбрано: 0 элементов")
        else:
            self.selectionInfoLabel.setText(
                f"Выбрано: {stats['total']} элементов "
                f"(организаций: {stats['organizations']}, отделов: {stats['departments']}, сотрудников: {stats['employees']})"
            )

    def _on_select(self):
        """Подтверждение выбора"""
        selected_ids = self.selection_manager.get_selected_ids()
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