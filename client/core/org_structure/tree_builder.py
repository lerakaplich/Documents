from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTreeWidgetItem

from .hierarchy_builder import HierarchyBuilder
from .selection_manager import SelectionManager


class TreeBuilder:
    """
    Построитель дерева для пикера.

    - build_org_items(): верхний уровень (все организации); у незагруженной
      организации есть потомок-заглушка «Загрузка…», чтобы появилась стрелка раскрытия;
    - fill_org_item(): заменяет заглушку содержимым организации;
    - build_search_items(): отфильтрованное дерево для результатов поиска.
    """

    NODE_TYPE_PLACEHOLDER = 0
    NODE_TYPE_ORGANIZATION = 1
    NODE_TYPE_DEPARTMENT = 2
    NODE_TYPE_EMPLOYEE = 3

    def __init__(
        self,
        builder: HierarchyBuilder,
        selection_manager: SelectionManager,
        allow_org_select: bool = True,
    ):
        self.builder = builder
        self.selection_manager = selection_manager
        self.allow_org_select = allow_org_select

    # ───────────────────────── ленивое дерево ─────────────────────────

    def build_org_items(self) -> list[QTreeWidgetItem]:
        items = []
        for org_id, org in self.builder.organizations.items():
            item = self._create_organization_item(org_id, org)
            if self.builder.is_loaded(org_id):
                self._fill(item, org_id)
            else:
                self._add_placeholder(item)
            items.append(item)
        return items

    def fill_org_item(self, org_item: QTreeWidgetItem, org_id: int):
        """Заменяет содержимое организации (заглушку) загруженными данными."""
        org_item.takeChildren()
        self._fill(org_item, org_id)

    def set_placeholder_text(self, org_item: QTreeWidgetItem, text: str):
        if org_item.childCount() == 1:
            data = org_item.child(0).data(0, Qt.ItemDataRole.UserRole) or {}
            if data.get("type") == self.NODE_TYPE_PLACEHOLDER:
                org_item.child(0).setText(0, text)

    def _fill(self, org_item: QTreeWidgetItem, org_id: int):
        struct = self.builder.build_org(org_id)
        self._add_departments(org_item, struct["departments"])
        if struct["employees"]:
            self._add_employee_group(org_item, struct["employees"])

    def _add_placeholder(self, parent: QTreeWidgetItem):
        item = QTreeWidgetItem(parent)
        item.setText(0, "Загрузка…")
        item.setData(0, Qt.ItemDataRole.UserRole, {"type": self.NODE_TYPE_PLACEHOLDER, "id": -1, "name": ""})
        item.setFlags(Qt.ItemFlag.ItemIsEnabled)

    # ───────────────────────── поиск ─────────────────────────

    def build_search_items(self, query: str) -> list[QTreeWidgetItem]:
        """
        Результаты поиска (данные всех организаций уже должны быть загружены):
        - совпал сотрудник → организация → цепочка отделов → только он;
        - совпал отдел → организация → цепочка отделов → найденный отдел
          со всем поддеревом и всеми сотрудниками;
        - совпала организация → организация целиком.
        """
        q = query.lower().strip()
        items = []
        for org_id, org in self.builder.organizations.items():
            struct = self.builder.build_org(org_id)
            org_match = q in (org.get("name") or "").lower()

            org_item = self._create_organization_item(org_id, org)
            self._add_departments_filtered(org_item, struct["departments"], q, org_match)
            emps = [e for e in struct["employees"] if org_match or q in (e.get("name") or "").lower()]
            if emps:
                self._add_employee_group(org_item, emps)

            if org_match or org_item.childCount():
                org_item.setExpanded(True)
                items.append(org_item)
        return items

    def _add_departments_filtered(self, parent: QTreeWidgetItem, dept_structs: list[dict], q: str, force: bool):
        for ds in dept_structs:
            dept = ds["department"]
            label = f"{dept.get('number') or ''} {dept.get('name') or ''}".lower()
            dept_match = force or q in label

            item = self._create_department_item(dept)
            self._add_departments_filtered(item, ds["children"], q, dept_match)
            emps = [e for e in ds["employees"] if dept_match or q in (e.get("name") or "").lower()]
            if emps:
                self._add_employee_group(item, emps)

            if dept_match or item.childCount():
                parent.addChild(item)
                item.setExpanded(True)

    # ───────────────────────── элементы ─────────────────────────

    def _setup_checkable(self, item: QTreeWidgetItem, node_type: int, node_id: int, checkable: bool = True):
        if not checkable:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
            return
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        selected = self.selection_manager.is_selected(node_id, node_type)
        item.setCheckState(0, Qt.CheckState.Checked if selected else Qt.CheckState.Unchecked)

    def _create_organization_item(self, org_id: int, org: dict) -> QTreeWidgetItem:
        item = QTreeWidgetItem()
        item.setText(0, org.get("name", ""))
        item.setData(
            0,
            Qt.ItemDataRole.UserRole,
            {"type": self.NODE_TYPE_ORGANIZATION, "id": org_id, "name": org.get("name", "")},
        )
        self._setup_checkable(item, self.NODE_TYPE_ORGANIZATION, org_id, checkable=self.allow_org_select)
        return item

    def _create_department_item(self, dept: dict) -> QTreeWidgetItem:
        dept_name = dept.get("name", "")
        label = f"{dept['number']}. {dept_name}" if dept.get("number") else dept_name

        item = QTreeWidgetItem()
        item.setText(0, label)
        item.setData(
            0,
            Qt.ItemDataRole.UserRole,
            {"type": self.NODE_TYPE_DEPARTMENT, "id": dept["id"], "name": dept_name},
        )
        self._setup_checkable(item, self.NODE_TYPE_DEPARTMENT, dept["id"])
        return item

    @staticmethod
    def _employee_label(emp: dict) -> str:
        last = emp.get("last_name") or ""
        first = emp.get("first_name") or ""
        patr = emp.get("patronymic") or ""
        if not (last or first):
            return emp.get("name") or f"ID: {emp.get('id')}"
        label = last
        if first:
            label += f" {first[0]}."
        if patr:
            label += f" {patr[0]}."
        if emp.get("position"):
            label += f" ({emp['position']})"
        return label.strip()

    def _create_employee_item(self, emp: dict) -> QTreeWidgetItem:
        item = QTreeWidgetItem()
        item.setText(0, self._employee_label(emp))
        item.setData(
            0,
            Qt.ItemDataRole.UserRole,
            {"type": self.NODE_TYPE_EMPLOYEE, "id": emp["id"], "name": emp.get("name", "")},
        )
        self._setup_checkable(item, self.NODE_TYPE_EMPLOYEE, emp["id"])
        return item

    def _add_departments(self, parent: QTreeWidgetItem, departments: list[dict]):
        for ds in departments:
            dept_item = self._create_department_item(ds["department"])
            parent.addChild(dept_item)
            if ds["children"]:
                self._add_departments(dept_item, ds["children"])
            if ds["employees"]:
                self._add_employee_group(dept_item, ds["employees"])

    def _add_employee_group(self, parent: QTreeWidgetItem, employees: list[dict]):
        group_item = QTreeWidgetItem(parent)
        group_item.setText(0, "Сотрудники")
        group_item.setData(
            0,
            Qt.ItemDataRole.UserRole,
            {"type": self.NODE_TYPE_DEPARTMENT, "id": -1, "name": "Сотрудники"},
        )
        group_item.setFlags(group_item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
        for emp in employees:
            group_item.addChild(self._create_employee_item(emp))