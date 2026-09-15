# client/services/org_service.py

"""
Сервис для работы с организациями через API
"""
import logging
from typing import List, Dict, Any, Optional

from client.core.http_client import HttpClient

logger = logging.getLogger(__name__)


class OrgService:
    """Сервис для управления организациями"""

    def __init__(self, http_client: HttpClient):
        self.http = http_client
        self.base_path = "/org"

    def get_all_organizations(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Получить все организации"""
        try:
            logger.info("📥 Запрос на получение организаций...")

            response = self.http.get(
                f"{self.base_path}",
                params={"limit": limit, "offset": offset}
            )

            logger.info(f"📥 Получен ответ: {response}")
            if isinstance(response, list):
                return response
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка получения организаций: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_organization(self, org_id: int) -> Optional[Dict[str, Any]]:
        """Получить организацию по ID"""
        try:
            response = self.http.get(f"{self.base_path}/{org_id}")
            return response
        except Exception as e:
            logger.error(f"Ошибка получения организации {org_id}: {e}")
            return None

    def get_org_structure(self, org_id: int) -> List[Dict[str, Any]]:
        """Получить структуру организации"""
        try:
            response = self.http.get(f"{self.base_path}/{org_id}/structure")
            if isinstance(response, list):
                return response
            return []
        except Exception as e:
            logger.error(f"Ошибка получения структуры организации {org_id}: {e}")
            return []

    # client/services/org_service.py

    def create_organization(self, org_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создать новую организацию"""
        try:
            # Формируем данные для сервера
            server_data = {
                'name': org_data.get('name', ''),
                'full_name': org_data.get('full_name', ''),
                'short_name': org_data.get('short_name', ''),
                'unp': org_data.get('unp', ''),
                'address': org_data.get('address', ''),
                'phone_number': org_data.get('phone_number', org_data.get('phone', '')),  # Приоритет phone_number
                'email': org_data.get('email', ''),
                'director': org_data.get('director', ''),
                'smdo_code': org_data.get('smdo_code', ''),
                'is_subscriber': org_data.get('is_subscriber', False)
            }

            response = self.http.post(
                f"{self.base_path}",
                json=server_data
            )
            logger.info(f"✅ Организация создана: {response}")
            return response
        except Exception as e:
            logger.error(f"❌ Ошибка создания организации: {e}")
            return None

    def update_organization(self, org_id: int, org_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновить организацию"""
        try:
            # Формируем данные для сервера
            server_data = {
                'name': org_data.get('name', ''),
                'full_name': org_data.get('full_name', ''),
                'short_name': org_data.get('short_name', ''),
                'unp': org_data.get('unp', ''),
                'address': org_data.get('address', ''),
                'phone_number': org_data.get('phone_number', org_data.get('phone', '')),  # Приоритет phone_number
                'email': org_data.get('email', ''),
                'director': org_data.get('director', ''),
                'smdo_code': org_data.get('smdo_code', ''),
                'is_subscriber': org_data.get('is_subscriber', False)
            }

            response = self.http.patch(
                f"{self.base_path}/{org_id}",
                json=server_data
            )
            logger.info(f"✅ Организация обновлена: {response}")
            return response
        except Exception as e:
            logger.error(f"❌ Ошибка обновления организации {org_id}: {e}")
            return None


    def delete_organization(self, org_id: int) -> bool:
        """Удалить организацию"""
        try:
            self.http.delete(f"{self.base_path}/{org_id}")
            logger.info(f"✅ Организация {org_id} удалена")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка удаления организации {org_id}: {e}")
            return False

    def get_org_employees(self, org_id: int):
        """Список сотрудников организации (с positions)."""
        try:
            response = self.http.get(f"{self.base_path}/{org_id}/employees")
            return response if isinstance(response, list) else []
        except Exception as e:
            logger.error(f"Ошибка получения сотрудников орг {org_id}: {e}")
            return []

# Синглтон
_org_service_instance: Optional[OrgService] = None


def get_org_service(http_client: HttpClient) -> OrgService:
    """Получить экземпляр OrgService"""
    global _org_service_instance
    if _org_service_instance is None:
        _org_service_instance = OrgService(http_client)
    return _org_service_instance