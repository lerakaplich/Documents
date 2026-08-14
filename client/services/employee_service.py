# client/services/employee_service.py
from typing import Optional, Dict, Any, List
from client.core.http_client import HttpClient


class EmployeeService:
    """Сервис для работы с API сотрудников"""

    def __init__(self, http_client: HttpClient):
        self.client = http_client

    def get_my_profile(self) -> Dict[str, Any]:
        """Получить профиль текущего пользователя через /me"""
        return self.client.get("/employees/me")

    def get_employee(self, employee_id: int) -> Dict[str, Any]:
        """Получить профиль сотрудника по ID"""
        return self.client.get(f"/employees/{employee_id}")

    def get_all_employees(
            self,
            page: int = 1,
            limit: int = 100,
            show_fired: bool = False
    ) -> Dict[str, Any]:
        """
        Получить всех сотрудников с пагинацией

        Returns:
            Dict с полями: items, total, page, limit
        """
        return self.client.get(
            "/employees/all",
            params={"page": page, "limit": limit, "show_fired": show_fired}
        )

    def get_department_staff(self, department_id: int) -> List[Dict[str, Any]]:
        """Получить сотрудников подразделения"""
        return self.client.get(f"/employees/departments/{department_id}/staff")

    def create_employee(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Создать сотрудника"""
        return self.client.post("/employees", json=data)

    def update_my_profile(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить профиль текущего пользователя"""
        return self.client.patch("/employees/me/profile", data)

    def update_employee(self, employee_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить данные сотрудника (только для руководителей)"""
        return self.client.patch(f"/employees/{employee_id}", data)

    def toggle_access_leadership(self, position_id: int, is_leader: bool) -> Dict[str, Any]:
        """Переключить доступ руководителя"""
        return self.client.patch(
            f"/employees/{position_id}/positions/{position_id}/toggle-access",
            params={"is_leader": is_leader}
        )