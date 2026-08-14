# client/services/org_service.py
from typing import Optional, Dict, Any, List
from client.core.http_client import HttpClient


class OrgService:
    """Сервис для работы с API организаций и подразделений"""

    def __init__(self, http_client: HttpClient):
        self.client = http_client

    # ==================== ОРГАНИЗАЦИИ ====================

    def get_organizations(self) -> List[Dict[str, Any]]:
        """Получить список всех организаций"""
        return self.client.get("/organizations")

    def get_organization(self, org_id: int) -> Dict[str, Any]:
        """Получить организацию по ID"""
        return self.client.get(f"/organizations/{org_id}")

    def create_organization(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать организацию"""
        return self.client.post("/organizations", json=data)

    def update_organization(self, org_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить организацию"""
        return self.client.put(f"/organizations/{org_id}", json=data)

    def delete_organization(self, org_id: int) -> Dict[str, Any]:
        """Удалить организацию"""
        return self.client.delete(f"/organizations/{org_id}")

    # ==================== ПОДРАЗДЕЛЕНИЯ ====================

    def get_departments(self, org_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получить список подразделений (опционально по организации)"""
        params = {}
        if org_id is not None:
            params["organization_id"] = org_id
        return self.client.get("/departments", params=params)

    def get_department_tree(self, org_id: int) -> List[Dict[str, Any]]:
        """Получить дерево подразделений организации"""
        return self.client.get(f"/departments/tree/{org_id}")

    def get_department(self, dept_id: int) -> Dict[str, Any]:
        """Получить подразделение по ID"""
        return self.client.get(f"/departments/{dept_id}")

    def get_department_children(self, dept_id: int) -> List[Dict[str, Any]]:
        """Получить дочерние подразделения"""
        return self.client.get(f"/departments/{dept_id}/children")

    def get_department_staff(self, dept_id: int) -> List[Dict[str, Any]]:
        """Получить сотрудников подразделения"""
        return self.client.get(f"/employees/departments/{dept_id}/staff")

    def create_department(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать подразделение"""
        return self.client.post("/departments", json=data)

    def update_department(self, dept_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить подразделение"""
        return self.client.put(f"/departments/{dept_id}", json=data)

    def delete_department(self, dept_id: int) -> Dict[str, Any]:
        """Удалить подразделение"""
        return self.client.delete(f"/departments/{dept_id}")