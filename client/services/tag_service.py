# client/services/tag_service.py

"""
Сервис для работы с тегами через API
"""
import logging
from typing import List, Dict, Any, Optional

from client.core.http_client import HttpClient

logger = logging.getLogger(__name__)


class TagService:
    """Сервис для управления тегами"""

    def __init__(self, http_client: HttpClient):
        self.http = http_client
        self.base_path = "/tag"

    def get_all_tags(self) -> List[Dict[str, Any]]:
        """Получить все теги"""
        try:
            response = self.http.get(f"{self.base_path}")
            if isinstance(response, list):
                return response
            return []
        except Exception as e:
            logger.error(f"Ошибка получения тегов: {e}")
            return []

    def get_tag(self, tag_id: int) -> Optional[Dict[str, Any]]:
        """Получить тег по ID"""
        try:
            response = self.http.get(f"{self.base_path}/{tag_id}")
            return response
        except Exception as e:
            logger.error(f"Ошибка получения тега {tag_id}: {e}")
            return None

    def create_tag(self, tag_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создать новый тег"""
        try:
            response = self.http.post(
                f"{self.base_path}",
                json=tag_data
            )
            return response
        except Exception as e:
            logger.error(f"Ошибка создания тега: {e}")
            return None

    def update_tag(self, tag_id: int, tag_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновить тег"""
        try:
            response = self.http.patch(
                f"{self.base_path}/{tag_id}",
                json=tag_data
            )
            return response
        except Exception as e:
            logger.error(f"Ошибка обновления тега {tag_id}: {e}")
            return None

    def delete_tag(self, tag_id: int) -> bool:
        """Удалить тег"""
        try:
            self.http.delete(f"{self.base_path}/{tag_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления тега {tag_id}: {e}")
            return False


# Синглтон
_tag_service_instance: Optional[TagService] = None


def get_tag_service(http_client: HttpClient) -> TagService:
    """Получить экземпляр TagService"""
    global _tag_service_instance
    if _tag_service_instance is None:
        _tag_service_instance = TagService(http_client)
    return _tag_service_instance