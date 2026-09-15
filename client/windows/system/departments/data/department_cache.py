# client/windows/system/departments/data/department_cache.py
from typing import Dict, List, Any


class DepartmentCache:
    """Всё, что касается кэшей ленивой загрузки."""

    def __init__(self):
        self.children_nodes: Dict[int, list] = {}      # org/dept id → готовые узлы
        self.nodes_data: Dict[int, Dict[str, Any]] = {}  # id → сырые данные узла
        self.employees_by_dept: Dict[int, List[dict]] = {}  # dept_id → сотрудники
        self.organizations: List[dict] = []

    def clear(self):
        self.children_nodes.clear()
        self.nodes_data.clear()
        self.employees_by_dept.clear()