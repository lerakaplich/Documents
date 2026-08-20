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

    def create_department(self, dept_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создать новое подразделение"""
        try:
            # Формируем данные для сервера
            server_data = {
                'name': dept_data.get('name', ''),
                'organization_id': dept_data.get('organization_id'),
                'parent_id': dept_data.get('parent_department_id'),
                'type_id': dept_data.get('type_id'),
                'department_number': dept_data.get('department_number', ''),
                'phone': dept_data.get('phone', ''),
                'head_id': dept_data.get('head_id')
            }

            # Убираем None значения
            server_data = {k: v for k, v in server_data.items() if v is not None}

            response = self.http.post(
                f"{self.base_path}",
                json=server_data
            )
            logger.info(f"✅ Подразделение создано: {response}")
            return response
        except Exception as e:
            logger.error(f"❌ Ошибка создания подразделения: {e}")
            return None

    def update_department(self, dept_id: int, dept_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновить подразделение"""
        try:
            # Формируем данные для сервера
            server_data = {
                'name': dept_data.get('name'),
                'organization_id': dept_data.get('organization_id'),
                'parent_id': dept_data.get('parent_department_id'),
                'type_id': dept_data.get('type_id'),
                'department_number': dept_data.get('department_number'),
                'phone': dept_data.get('phone'),
                'head_id': dept_data.get('head_id')
            }

            # Убираем None значения
            server_data = {k: v for k, v in server_data.items() if v is not None}

            response = self.http.patch(
                f"{self.base_path}/{dept_id}",
                json=server_data
            )
            logger.info(f"✅ Подразделение обновлено: {response}")
            return response
        except Exception as e:
            logger.error(f"❌ Ошибка обновления подразделения {dept_id}: {e}")
            return None

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
                params={'new_head_id': head_id}
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


# Синглтон
_department_service_instance: Optional[DepartmentService] = None


def get_department_service(http_client: HttpClient) -> DepartmentService:
    """Получить экземпляр DepartmentService"""
    global _department_service_instance
    if _department_service_instance is None:
        _department_service_instance = DepartmentService(http_client)
    return _department_service_instance