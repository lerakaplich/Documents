# client/services/employee_service.py
from typing import Optional, Dict, Any
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

    def update_my_profile(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить профиль текущего пользователя"""
        return self.client.patch("/employees/me/profile", data)