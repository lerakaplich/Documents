# client/services/department_service.py

"""
Сервис для работы с подразделениями через API
"""
import logging
from typing import List, Dict, Any, Optional

from client.core.http_client import HttpClient

logger = logging.getLogger(__name__)


class DepartmentService:
    """Сервис для управления подразделениями"""

    def __init__(self, http_client: HttpClient):
        self.http = http_client
        self.base_path = "/departments"

    def get_department(self, dept_id: int) -> Optional[Dict[str, Any]]:
        """Получить подразделение по ID"""
        try:
            response = self.http.get(f"{self.base_path}/{dept_id}")
            return response
        except Exception as e:
            logger.error(f"Ошибка получения подразделения {dept_id}: {e}")
            return None

    def create_department(self, dept_data):
        return self.http.post(f"{self.base_path}", json=dept_data)

    def update_department(self, dept_id, dept_data):
        return self.http.patch(f"{self.base_path}/{dept_id}", json=dept_data)

    def delete_department(self, dept_id: int) -> bool:
        """Удалить подразделение"""
        try:
            self.http.delete(f"{self.base_path}/{dept_id}")
            logger.info(f"✅ Подразделение {dept_id} удалено")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка удаления подразделения {dept_id}: {e}")
            return False

    def move_department(self, dept_id: int, new_parent_id: Optional[int]) -> bool:
        """Переместить подразделение"""
        try:
            server_data = {'new_parent_id': new_parent_id}
            self.http.patch(
                f"{self.base_path}/{dept_id}/move",
                json=server_data
            )
            logger.info(f"✅ Подразделение {dept_id} перемещено")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка перемещения подразделения {dept_id}: {e}")
            return False

    def set_department_head(self, dept_id: int, head_id: int) -> bool:
        """Назначить руководителя подразделения"""
        try:
            self.http.patch(
                f"{self.base_path}/{dept_id}/head",
                json={'new_head_id': head_id}  # ← теперь правильно
            )
            logger.info(f"✅ Назначен руководитель для подразделения {dept_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка назначения руководителя {dept_id}: {e}")
            return False

    def remove_department_head(self, dept_id: int) -> bool:
        """Убрать руководителя подразделения"""
        try:
            self.http.delete(f"{self.base_path}/{dept_id}/head")
            logger.info(f"✅ Руководитель убран у подразделения {dept_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка удаления руководителя {dept_id}: {e}")
            return False

    def get_department_staff(self, dept_id: int) -> List[Dict[str, Any]]:
        """Сотрудники подразделения (GET /departments/{id}/staff)."""
        try:
            response = self.http.get(f"{self.base_path}/{dept_id}/staff")
            return response if isinstance(response, list) else []
        except Exception as e:
            logger.error(f"Ошибка получения сотрудников подразделения {dept_id}: {e}")
            return []

# Синглтон
_department_service_instance: Optional[DepartmentService] = None


def get_department_service(http_client: HttpClient) -> DepartmentService:
    """Получить экземпляр DepartmentService"""
    global _department_service_instance
    if _department_service_instance is None:
        _department_service_instance = DepartmentService(http_client)
    return _department_service_instance