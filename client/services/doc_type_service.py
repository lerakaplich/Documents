# client/services/doc_type_service.py

"""
Сервис для работы с типами документов через API
"""
import logging
from typing import List, Dict, Any, Optional

from client.core.http_client import HttpClient

logger = logging.getLogger(__name__)


class DocTypeService:
    """Сервис для управления типами документов"""

    def __init__(self, http_client: HttpClient):
        self.http = http_client
        self.base_path = "/doc-types"

    def get_all_types(self) -> List[Dict[str, Any]]:
        """Получить все типы документов"""
        try:
            logger.info("📥 Запрос на получение типов документов...")

            # Пробуем отправить запрос с явными параметрами
            response = self.http.get(
                f"{self.base_path}",
                params={}  # Явно передаем пустые параметры
            )

            logger.info(f"📥 Получен ответ: {response}")
            if isinstance(response, list):
                return response
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка получения типов документов: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_type(self, type_id: int) -> Optional[Dict[str, Any]]:
        """Получить тип документа по ID"""
        try:
            response = self.http.get(f"{self.base_path}/{type_id}")
            return response
        except Exception as e:
            logger.error(f"Ошибка получения типа {type_id}: {e}")
            return None

    # client/services/doc_type_service.py

    def create_type(self, type_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Создать новый тип документа"""
        try:
            # Убедимся, что отправляем правильные поля
            server_data = {
                'name': type_data.get('name', ''),
                'fields': type_data.get('fields', {}),
                'auto_num': type_data.get('auto_num', False),
                'smdo_code_type': type_data.get('smdo_code_type', '')
            }

            response = self.http.post(
                f"{self.base_path}",
                json=server_data
            )
            logger.info(f"✅ Тип документа создан: {response}")
            return response
        except Exception as e:
            logger.error(f"❌ Ошибка создания типа документа: {e}")
            return None

    def update_type(self, type_id: int, type_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Обновить тип документа"""
        try:
            # Убедимся, что отправляем правильные поля
            server_data = {
                'name': type_data.get('name', ''),
                'fields': type_data.get('fields', {}),
                'auto_num': type_data.get('auto_num', False),
                'smdo_code_type': type_data.get('smdo_code_type', '')
            }

            response = self.http.patch(
                f"{self.base_path}/{type_id}",
                json=server_data
            )
            logger.info(f"✅ Тип документа обновлен: {response}")
            return response
        except Exception as e:
            logger.error(f"❌ Ошибка обновления типа {type_id}: {e}")
            return None

    def delete_type(self, type_id: int) -> bool:
        """Удалить тип документа"""
        try:
            self.http.delete(f"{self.base_path}/{type_id}")
            logger.info(f"✅ Тип документа {type_id} удален")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка удаления типа {type_id}: {e}")
            return False

    def get_types_grouped(self) -> List[Dict[str, Any]]:
        """
        Возвращает список групп для LeftPanel.load_from_data().
        Все типы показываются и во «Внутренних», и во «Внешних» —
        потому что каждый тип может быть использован в обоих направлениях.
        """
        types = self.get_all_types()

        if not types:
            return []

        # Один и тот же список для обеих групп.
        # Копируем dict'ы, чтобы будущие изменения в UI не пересекались.
        directions = [
            {"name": t.get("name") or "—", "type_id": t.get("id")}
            for t in types
            if t.get("id") is not None
        ]

        return [
            {"group": "Внешние документы", "directions": list(directions)},
            {"group": "Внутренние документы", "directions": list(directions)},
        ]

# Синглтон
_doc_type_service_instance: Optional[DocTypeService] = None


def get_doc_type_service(http_client: HttpClient) -> DocTypeService:
    """Получить экземпляр DocTypeService"""
    global _doc_type_service_instance
    if _doc_type_service_instance is None:
        _doc_type_service_instance = DocTypeService(http_client)
    return _doc_type_service_instance