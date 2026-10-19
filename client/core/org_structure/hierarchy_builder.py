from collections import defaultdict
from typing import Any


class HierarchyBuilder:
    """
    Иерархия организаций с ленивым добавлением данных.

    - Список организаций известен сразу.
    - Отделы и сотрудники каждой организации добавляются через add_org_data().
    - Словари self.departments / self.employees — одни и те же объекты на всё
      время жизни (их держит SelectionManager), поэтому они только пополняются.
    - Если departments/employees переданы в конструктор (режим «всё уже есть»),
      все организации считаются загруженными.
    """

    def __init__(
        self,
        organizations: list[dict],
        departments: list[dict] | None = None,
        employees: list[dict] | None = None,
    ):
        self.organizations: dict[int, dict] = {org["id"]: org for org in organizations}
        self.departments: dict[int, dict] = {}
        self.employees: dict[int, dict] = {}

        self._children: dict[int, list[dict]] = defaultdict(list)
        self._roots_by_org: dict[int, list[dict]] = defaultdict(list)
        self._emps_by_dept: dict[int, list[dict]] = defaultdict(list)
        self._emps_no_dept_by_org: dict[int, list[dict]] = defaultdict(list)
        self._loaded_orgs: set[int] = set()

        if departments or employees:
            self._index(departments or [], employees or [])
            self._loaded_orgs = set(self.organizations)

    # ── ленивая подгрузка ───────────────────────────────────────────

    def is_loaded(self, org_id: int) -> bool:
        return org_id in self._loaded_orgs

    def add_org_data(self, org_id: int, departments: list[dict], employees: list[dict]):
        """Добавляет отделы и сотрудников организации (повторный вызов игнорируется)."""
        if org_id in self._loaded_orgs:
            return
        self._index(departments, employees)
        self._loaded_orgs.add(org_id)

    def _index(self, departments: list[dict], employees: list[dict]):
        for dept in departments:
            if dept["id"] in self.departments:
                continue
            self.departments[dept["id"]] = dept
            parent_id = dept.get("parent_id")
            if parent_id is None:
                self._roots_by_org[dept["organization_id"]].append(dept)
            else:
                self._children[parent_id].append(dept)

        for emp in employees:
            if emp["id"] in self.employees:
                continue
            self.employees[emp["id"]] = emp
            positions = emp.get("positions") or []
            dept_ids = {p.get("department_id") for p in positions if p.get("department_id") is not None}
            for dept_id in dept_ids:
                self._emps_by_dept[dept_id].append(emp)
            if not any(d in self.departments for d in dept_ids):
                org_id = emp.get("organization_id")
                if org_id is not None:
                    self._emps_no_dept_by_org[org_id].append(emp)

    # ── потомки узла (по данным, а не по виджетам) ──────────────────

    def descendants(self, node_type: int, node_id: int) -> tuple[set[int], set[int]]:
        """
        Для организации (1) или отдела (2) возвращает (id отделов, id сотрудников)
        всех загруженных потомков. Сам узел в результат не входит.
        """
        dept_ids: set[int] = set()
        emp_ids: set[int] = set()

        if node_type == 1:
            dept_ids = {d_id for d_id, d in self.departments.items() if d.get("organization_id") == node_id}
            emp_ids = {e_id for e_id, e in self.employees.items() if e.get("organization_id") == node_id}
        elif node_type == 2:
            stack = [c["id"] for c in self._children.get(node_id, [])]
            while stack:
                d_id = stack.pop()
                if d_id in dept_ids:
                    continue
                dept_ids.add(d_id)
                stack.extend(c["id"] for c in self._children.get(d_id, []))
            emp_ids |= {e["id"] for e in self._emps_by_dept.get(node_id, [])}
        else:
            return dept_ids, emp_ids

        for d_id in dept_ids:
            emp_ids |= {e["id"] for e in self._emps_by_dept.get(d_id, [])}
        return dept_ids, emp_ids

    # ── построение структур для дерева ──────────────────────────────

    def build_org(self, org_id: int) -> dict[str, Any]:
        return {
            "organization": self.organizations[org_id],
            "loaded": org_id in self._loaded_orgs,
            "departments": [self._build_department_tree(d) for d in self._roots_by_org.get(org_id, [])],
            "employees": self._emps_no_dept_by_org.get(org_id, []),
        }

    def build(self) -> dict[int, dict[str, Any]]:
        return {org_id: self.build_org(org_id) for org_id in self.organizations}

    def _build_department_tree(self, dept: dict) -> dict:
        return {
            "department": dept,
            "children": [self._build_department_tree(c) for c in self._children.get(dept["id"], [])],
            "employees": self._emps_by_dept.get(dept["id"], []),
        }