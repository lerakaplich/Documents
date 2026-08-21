# client/services/employee_service.py
from typing import Optional, Dict, Any, List
from client.core.http_client import HttpClient


class EmployeeService:
    """Сервис для работы с API сотрудников"""

    def __init__(self, http_client: HttpClient):
        self.client = http_client

    def get_my_profile(self) -> Dict[str, Any]:
        """Получить профиль текущего пользователя через /me"""
        try:
            print("📤 Отправка запроса на /employees/me")
            result = self.client.get("/employees/me")
            print(f"📥 Получен ответ: {result}")
            return result
        except Exception as e:
            print(f"❌ Ошибка в get_my_profile: {e}")
            raise

    def get_employee(self, employee_id: int) -> Dict[str, Any]:
        """Получить профиль сотрудника по ID"""
        return self.client.get(f"/employees/{employee_id}")

    def update_my_profile(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Обновить профиль текущего пользователя"""
        return self.client.patch("/employees/me/profile", data=data)

    def get_all_employees(self, limit: int = 1000, offset: int = 0, show_fired: bool = False) -> List[Dict[str, Any]]:
        """
        Получить список всех сотрудников
        GET /employees/all

        Args:
            limit: количество записей
            offset: смещение
            show_fired: показывать уволенных

        Returns:
            List[Dict]: список сотрудников
        """
        try:
            print(f"📤 Запрос на получение сотрудников (limit={limit}, show_fired={show_fired})")
            result = self.client.get(
                "/employees/all",
                params={"limit": limit, "offset": offset, "show_fired": show_fired}
            )

            # Обрабатываем ответ - он может быть списком или объектом с items
            if isinstance(result, list):
                print(f"📥 Получено {len(result)} сотрудников")
                return result
            elif isinstance(result, dict):
                items = result.get('items', [])
                print(f"📥 Получено {len(items)} сотрудников")
                return items
            else:
                return []
        except Exception as e:
            print(f"❌ Ошибка получения сотрудников: {e}")
            import traceback
            traceback.print_exc()
            return []