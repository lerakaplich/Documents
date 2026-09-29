# client/windows/system/departments/data/department_cache.py
from typing import Any


class DepartmentCache:
    """Всё, что касается кэшей ленивой загрузки."""

    def __init__(self):
        self.children_nodes: dict[int, list] = {}  # org/dept id → готовые узлы
        self.nodes_data: dict[int, dict[str, Any]] = {}  # id → сырые данные узла
        self.employees_by_dept: dict[int, list[dict]] = {}  # dept_id → сотрудники
        self.organizations: list[dict] = []

    def clear(self):
        self.children_nodes.clear()
        self.nodes_data.clear()
        self.employees_by_dept.clear()
