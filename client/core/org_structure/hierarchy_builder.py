from collections import defaultdict
from typing import Any


class HierarchyBuilder:
    """Строитель иерархической структуры организаций"""

    def __init__(self, organizations: list[dict], departments: list[dict], employees: list[dict]):
        self.organizations = {org["id"]: org for org in organizations}
        self.departments = {dept["id"]: dept for dept in departments}
        self.employees = {emp["id"]: emp for emp in employees}

        # индексы, чтобы не перебирать все списки для каждого узла
        self._children: dict[int | None, list[dict]] = defaultdict(list)
        self._roots_by_org: dict[int, list[dict]] = defaultdict(list)
        for dept in self.departments.values():
            parent_id = dept.get("parent_id")
            if parent_id is None:
                self._roots_by_org[dept["organization_id"]].append(dept)
            else:
                self._children[parent_id].append(dept)

        self._emps_by_dept: dict[int, list[dict]] = defaultdict(list)
        self._emps_no_dept_by_org: dict[int, list[dict]] = defaultdict(list)
        for emp in self.employees.values():
            positions = emp.get("positions", [])
            dept_ids = {p.get("department_id") for p in positions if p.get("department_id") is not None}
            for dept_id in dept_ids:
                self._emps_by_dept[dept_id].append(emp)
            if not any(d in self.departments for d in dept_ids):
                org_id = emp.get("organization_id")
                if org_id is not None:
                    self._emps_no_dept_by_org[org_id].append(emp)

    def build(self) -> dict[int, dict[str, Any]]:
        hierarchy = {}
        for org_id, org in self.organizations.items():
            hierarchy[org_id] = {
                "organization": org,
                "departments": [self._build_department_tree(d) for d in self._roots_by_org.get(org_id, [])],
                "employees": self._emps_no_dept_by_org.get(org_id, []),
            }
        return hierarchy

    def _build_department_tree(self, dept: dict) -> dict:
        return {
            "department": dept,
            "children": [self._build_department_tree(c) for c in self._children.get(dept["id"], [])],
            "employees": self._emps_by_dept.get(dept["id"], []),
        }