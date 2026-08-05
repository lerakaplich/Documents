from typing import Dict, List, Any, Optional
from PyQt6.QtWidgets import QTreeWidgetItem
from PyQt6.QtCore import Qt

from .selection_manager import SelectionManager
from .tree_filter import TreeFilter


class TreeBuilder:
    """Построитель дерева для отображения"""

    NODE_TYPE_ORGANIZATION = 1
    NODE_TYPE_DEPARTMENT = 2
    NODE_TYPE_EMPLOYEE = 3

    def __init__(self, hierarchy: Dict[int, Dict], selection_manager: SelectionManager):
        self.hierarchy = hierarchy
        self.selection_manager = selection_manager

    def build_tree(self, filter_text: str = "") -> List[QTreeWidgetItem]:
        """Строит дерево"""
        items = []
        filter_lower = filter_text.lower().strip()

        for org_id, org_struct in self.hierarchy.items():
            org = org_struct['organization']

            if filter_lower and filter_lower not in org['name'].lower():
                if not TreeFilter.has_match_in_children(org_struct, filter_lower):
                    continue

            org_item = self._create_organization_item(org_id, org)
            self._add_departments(org_item, org_struct['departments'], filter_lower)
            self._add_employees(org_item, org_struct['employees'], filter_lower)

            if filter_lower and TreeFilter.has_match_in_node(org_item, filter_lower):
                org_item.setExpanded(True)

            items.append(org_item)

        return items

    def _create_organization_item(self, org_id: int, org: Dict) -> QTreeWidgetItem:
        item = QTreeWidgetItem()
        item.setText(0, org['name'])
        item.setData(0, Qt.ItemDataRole.UserRole, {
            'type': self.NODE_TYPE_ORGANIZATION,
            'id': org_id,
            'name': org['name']
        })
        self._setup_checkable(item)
        if self.selection_manager.is_selected(org_id):
            item.setCheckState(0, Qt.CheckState.Checked)
        return item

    def _create_department_item(self, dept: Dict) -> QTreeWidgetItem:
        dept_name = dept['name']
        if dept.get('number'):
            dept_name = f"{dept['number']}. {dept_name}"

        item = QTreeWidgetItem()
        item.setText(0, dept_name)
        item.setData(0, Qt.ItemDataRole.UserRole, {
            'type': self.NODE_TYPE_DEPARTMENT,
            'id': dept['id'],
            'name': dept['name']
        })
        self._setup_checkable(item)
        if self.selection_manager.is_selected(dept['id']):
            item.setCheckState(0, Qt.CheckState.Checked)
        return item

    def _create_employee_item(self, emp: Dict) -> QTreeWidgetItem:
        emp_name = f"{emp['last_name']} {emp['first_name'][0]}. {emp['patronymic'][0] if emp.get('patronymic') else ''}"
        if emp.get('position'):
            emp_name += f" ({emp['position']})"

        item = QTreeWidgetItem()
        item.setText(0, emp_name)
        item.setData(0, Qt.ItemDataRole.UserRole, {
            'type': self.NODE_TYPE_EMPLOYEE,
            'id': emp['id'],
            'name': emp['name']
        })
        self._setup_checkable(item)
        if self.selection_manager.is_selected(emp['id']):
            item.setCheckState(0, Qt.CheckState.Checked)
        return item

    def _setup_checkable(self, item: QTreeWidgetItem):
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Unchecked)

    def _add_departments(self, parent: QTreeWidgetItem, departments: List[Dict], filter_text: str):
        for dept_struct in departments:
            dept = dept_struct['department']

            if filter_text and filter_text not in dept['name'].lower():
                if not TreeFilter.has_match_in_children(dept_struct, filter_text):
                    continue

            dept_item = self._create_department_item(dept)
            parent.addChild(dept_item)

            if dept_struct['children']:
                self._add_departments(dept_item, dept_struct['children'], filter_text)

            if dept_struct['employees']:
                self._add_employee_group(dept_item, dept_struct['employees'], filter_text)

            if filter_text and TreeFilter.has_match_in_node(dept_item, filter_text):
                dept_item.setExpanded(True)

    def _add_employee_group(self, parent: QTreeWidgetItem, employees: List[Dict], filter_text: str):
        group_item = QTreeWidgetItem(parent)
        group_item.setText(0, "Сотрудники")
        group_item.setData(0, Qt.ItemDataRole.UserRole, {
            'type': self.NODE_TYPE_DEPARTMENT,
            'id': -1,
            'name': "Сотрудники"
        })
        group_item.setFlags(group_item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)

        for emp in employees:
            if filter_text and filter_text not in emp['name'].lower():
                continue
            emp_item = self._create_employee_item(emp)
            group_item.addChild(emp_item)

    def _add_employees(self, parent: QTreeWidgetItem, employees: List[Dict], filter_text: str):
        if employees:
            self._add_employee_group(parent, employees, filter_text)