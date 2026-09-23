import os
from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import QDialog, QTreeWidgetItem
from PyQt6.QtCore import pyqtSignal, Qt

from client.core.org_structure.hierarchy_builder import HierarchyBuilder
from client.core.org_structure.selection_manager import SelectionManager
from client.core.org_structure.tree_builder import TreeBuilder
from client.core.org_structure.employee_selection_data_loader import EmployeeSelectionDataLoader
from client.core.themes import apply_theme_to_widget
from client.windows.documents.table.create.employee_selection import EmployeeSelection


class EmployeeSelectionDialog(QDialog):
    """
    Диалог выбора получателей / исполнителей / отправителя.
    Если списки organizations / departments / employees пусты — грузит
    данные с сервера через http_client.
    """
    selection_confirmed = pyqtSignal(list)

    def __init__(self,
                 organizations: Optional[List[Dict[str, Any]]] = None,
                 departments: Optional[List[Dict[str, Any]]] = None,
                 employees: Optional[List[Dict[str, Any]]] = None,
                 preselected_ids: Optional[List[int]] = None,
                 parent=None,
                 title: str = "Выбор получателей",
                 instruction: str = "Выберите организации, отделы или сотрудников:",
                 http_client=None):

        super().__init__(parent)

        self._updating = False
        self.http_client = http_client or self._resolve_http_client()

        organizations = organizations or []
        departments = departments or []
        employees = employees or []

        # Если пришли пустые списки, но есть http_client — тянем с сервера
        if self.http_client and (not organizations or not departments or not employees):
            print("[EmployeeSelectionDialog] Списки пусты — грузим с сервера...")
            try:
                loader = EmployeeSelectionDataLoader(self.http_client)
                if not organizations:
                    organizations = loader.load_organizations()
                if not departments:
                    departments = loader.load_departments_flat()
                if not employees:
                    employees = loader.load_employees()
                # ── Диагностика ──
                print(
                    f"[EmployeeSelectionDialog] Данные для билдера: "
                    f"орг={len(organizations)}, "
                    f"отд={len(departments)}, "
                    f"сотр={len(employees)}"
                )
                if employees:
                    emp0 = employees[0]
                    print(f"[EmployeeSelectionDialog] первый сотрудник: keys={sorted(emp0.keys())}")
                    print(f"[EmployeeSelectionDialog] первый сотрудник: positions={emp0.get('positions')}")
            except Exception as e:
                print(f"[EmployeeSelectionDialog] Ошибка автозагрузки: {e}")
                import traceback
                traceback.print_exc()

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

    @staticmethod
    def _resolve_http_client():
        """Пробуем достать http_client из AppState, если он не передан."""
        try:
            from client.core.state.app_state import AppState
            return AppState().http_client
        except Exception:
            return None

    def _init_data(self, organizations, departments, employees, preselected_ids):
        self.builder = HierarchyBuilder(organizations, departments, employees)
        self.org_hierarchy = self.builder.build()

        self.selection_manager = SelectionManager(
            self.builder.organizations,
            self.builder.departments,
            self.builder.employees,
        )
        if preselected_ids:
            typed = []
            for node_id in preselected_ids:
                t = self._resolve_node_type(node_id)
                if t is not None:
                    typed.append((t, node_id))
            if typed:
                self.selection_manager.set_selected(typed)

        self.tree_builder = TreeBuilder(self.org_hierarchy, self.selection_manager)

    def _resolve_node_type(self, node_id):
        """Определяет тип узла: 1 = организация, 2 = отдел, 3 = сотрудник."""
        if node_id in self.builder.organizations:
            return 1
        if node_id in self.builder.departments:
            return 2
        if node_id in self.builder.employees:
            return 3
        return None

    def _init_ui(self, title: str, instruction: str):
        ui_path = EmployeeSelection.get_ui_path()
        EmployeeSelection.load_ui(self, ui_path)
        apply_theme_to_widget(self)

        if hasattr(self, "titleLabel"):
            self.titleLabel.setText(title)
        if hasattr(self, "instructionLabel"):
            self.instructionLabel.setText(instruction)

        if hasattr(self, "treeWidget"):
            self.treeWidget.setHeaderLabel("Структура организации")
            self.treeWidget.setIndentation(20)
            self.treeWidget.setItemsExpandable(True)

        base_dir = self._get_root_dir()
        EmployeeSelection.apply_checkbox_styles(self, base_dir)

    def reapply_theme(self):
        """Переприменить тему (вызывается через apply_theme_to_all_windows)."""
        apply_theme_to_widget(self)
        base_dir = self._get_root_dir()
        EmployeeSelection.apply_checkbox_styles(self, base_dir)

    def _get_root_dir(self) -> str:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = base_dir
        for _ in range(4):
            root_dir = os.path.dirname(root_dir)
        return root_dir

    def _connect_signals(self):
        if hasattr(self, "searchEdit"):
            self.searchEdit.textChanged.connect(self._on_search)
        if hasattr(self, "treeWidget"):
            self.treeWidget.itemChanged.connect(self._on_tree_item_changed)
        if hasattr(self, "selectButton"):
            self.selectButton.clicked.connect(self._on_select)
        if hasattr(self, "cancelButton"):
            self.cancelButton.clicked.connect(self.reject)

    # ─────────── логика чекбоксов / дерева (как было) ───────────

    def _on_tree_item_changed(self, item, column):
        if self._updating:
            return
        if not (item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
            return

        new_state = item.checkState(column)
        is_checked = (new_state == Qt.CheckState.Checked)

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        node_id = data.get("id")
        node_type = data.get("type")
        if node_id is None or node_id < 0 or node_type is None:
            return

        self._updating = True
        try:
            self.selection_manager.toggle(node_id, is_checked, node_type)

            all_descendants = self._get_all_descendants(item)
            descendant_items = set()
            for child_item in all_descendants:
                child_data = child_item.data(0, Qt.ItemDataRole.UserRole)
                if child_data and child_data.get("id") and child_data.get("id") > 0:
                    child_type = child_data.get("type")
                    if child_type is not None:
                        descendant_items.add((child_type, child_data["id"]))

            for child_type, child_id in descendant_items:
                self.selection_manager.toggle(child_id, is_checked, child_type)

            for child_item in all_descendants:
                child_data = child_item.data(0, Qt.ItemDataRole.UserRole)
                if child_data and child_data.get("id") and child_data.get("id") > 0:
                    child_item.setCheckState(
                        0,
                        Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked,
                    )

            if item.parent():
                self._update_parent_checks_only(item.parent())

            self._update_selection_info()
        finally:
            self._updating = False

    def _update_parent_checks_only(self, item):
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
        new_state = (
            Qt.CheckState.Checked if checked_count == total_count
            else Qt.CheckState.Unchecked
        )
        item.setCheckState(0, new_state)
        if item.parent():
            self._update_parent_checks_only(item.parent())

    def _get_all_descendants(self, item) -> List[QTreeWidgetItem]:
        descendants = []
        for i in range(item.childCount()):
            child = item.child(i)
            descendants.append(child)
            descendants.extend(self._get_all_descendants(child))
        return descendants

    def _populate_tree(self, filter_text: str = ""):
        if not hasattr(self, "treeWidget"):
            return

        self.treeWidget.blockSignals(True)
        try:
            self.treeWidget.clear()
            items = self.tree_builder.build_tree(filter_text)

            for item in items:
                self.treeWidget.addTopLevelItem(item)
                data = item.data(0, Qt.ItemDataRole.UserRole)
                if data and data.get("id") and data.get("id") > 0:
                    node_id = data["id"]
                    if self.selection_manager.is_selected(node_id):
                        item.setCheckState(0, Qt.CheckState.Checked)
                    else:
                        item.setCheckState(0, Qt.CheckState.Unchecked)
                    self._set_checkboxes_recursive(item)

            self._sync_all_checkboxes()
        finally:
            self.treeWidget.blockSignals(False)

    def _set_checkboxes_recursive(self, item):
        for i in range(item.childCount()):
            child = item.child(i)
            child_data = child.data(0, Qt.ItemDataRole.UserRole)
            if child_data and child_data.get("id") and child_data.get("id") > 0:
                node_id = child_data["id"]
                child.setCheckState(
                    0,
                    Qt.CheckState.Checked
                    if self.selection_manager.is_selected(node_id)
                    else Qt.CheckState.Unchecked,
                )
            self._set_checkboxes_recursive(child)

    def _sync_all_checkboxes(self):
        def sync_item(item):
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("id") and data.get("id") > 0:
                node_id = data["id"]
                is_selected = self.selection_manager.is_selected(node_id)
                item.setCheckState(
                    0,
                    Qt.CheckState.Checked if is_selected else Qt.CheckState.Unchecked,
                )
            for i in range(item.childCount()):
                sync_item(item.child(i))

        for i in range(self.treeWidget.topLevelItemCount()):
            sync_item(self.treeWidget.topLevelItem(i))

    def _on_search(self, text: str):
        """Поиск по дереву — фильтрует через TreeBuilder."""
        self._populate_tree(text)

    def _update_selection_info(self):
        if not hasattr(self, "selectionInfoLabel"):
            return
        selected_items = self.selection_manager.get_selected_items()

        org_count = dept_count = emp_count = 0
        for type_id, _ in selected_items:
            if type_id == 1:
                org_count += 1
            elif type_id == 2:
                dept_count += 1
            elif type_id == 3:
                emp_count += 1

        total = len(selected_items)
        if total == 0:
            self.selectionInfoLabel.setText("Выбрано: 0 элементов")
            return

        parts = [f"Выбрано: {total} элементов"]
        if org_count:
            parts.append(f"организаций: {org_count}")
        if dept_count:
            parts.append(f"отделов: {dept_count}")
        if emp_count:
            parts.append(f"сотрудников: {emp_count}")
        self.selectionInfoLabel.setText(" (".join(parts) + ")")

    def _on_select(self):
        selected_ids = self.selection_manager.get_selected_ids()
        self.selection_confirmed.emit(selected_ids)
        self.accept()

    # Public
    def get_selected_ids(self) -> List[int]:
        return self.selection_manager.get_selected_ids()

    def get_selected_organizations(self) -> List[Dict]:
        return self.selection_manager.get_selected_organizations()

    def get_selected_departments(self) -> List[Dict]:
        return self.selection_manager.get_selected_departments()

    def get_selected_employees(self) -> List[Dict]:
        return self.selection_manager.get_selected_employees()