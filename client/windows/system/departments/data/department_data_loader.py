# client/windows/system/departments/data/department_data_loader.py
from client.services.org_service import get_org_service
from .department_cache import DepartmentCache
from .department_data_indexer import index_tree, index_employees_by_department


class DepartmentDataLoader:
    """Загрузка и индексация данных об организациях / структуре / сотрудниках."""

    def __init__(self, http_client):
        self.http_client = http_client
        self.org_service = get_org_service(http_client)
        self.cache = DepartmentCache()

    # ─── Синхронные вызовы (выполняются в фоновом потоке через ApiTask) ───

    def fetch_organizations(self, limit: int = 200):
        return self.org_service.get_all_organizations(limit=limit) or []

    def fetch_org_bundle(self, org_id: int):
        """Возвращает (structure, employees) для организации."""
        structure = self.org_service.get_org_structure(org_id) or []
        if isinstance(structure, dict):
            structure = structure.get('children', [])

        employees = []
        try:
            # Пробуем разные методы сервиса
            for m in ('get_org_employees', 'get_organization_employees'):
                if hasattr(self.org_service, m):
                    employees = getattr(self.org_service, m)(org_id) or []
                    if employees:
                        break
            # Fallback — прямой запрос к эндпоинту
            if not employees:
                employees = self.http_client.get(f"/org/{org_id}/employees") or []
        except Exception as e:
            print(f"[WARN] employees for org {org_id}: {e}")

        # ─── Диагностика — что реально пришло ───
        print(f"[DEBUG] fetch_org_bundle(org_id={org_id}): "
              f"structure={len(structure)}, employees={len(employees)}")
        if employees:
            sample = employees[0]
            print(f"[DEBUG]   пример сотрудника: keys={sorted(sample.keys())}")
            print(f"[DEBUG]   positions={sample.get('positions')}")

        return structure, employees

    # ─── Применение загруженного к кэшу ───

    def apply_org_bundle(self, structure, employees):
        index_employees_by_department(self.cache, employees)
        index_tree(self.cache, structure)

    # ─── Геттеры ───

    def employees_for_department(self, dept_id: int):
        return self.cache.employees_by_dept.get(dept_id, [])

    def children_data_for_department(self, dept_id: int):
        node = self.cache.nodes_data.get(dept_id)
        if node and node.get('children'):
            return node['children']
        return []