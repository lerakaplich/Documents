# client/services/doc_type_service.py

"""
Сервис для работы с типами документов через API.

ПРЕДУПРЕЖДЕНИЕ: base_path = "/doc-types" не подтверждён реальным файлом
роутера (server/app/api/.../types.py или аналог в этой сессии не показывался).
Судя по паттерну с документами и вложениями (см. document_service.py,
attachment_service.py), где router монтируется под общим префиксом
"/documents", итоговый путь МОЖЕТ оказаться "/documents/doc-types", а не
голым "/doc-types". Если get_all_types()/get_type() будут возвращать 404 —
в первую очередь проверьте это.
"""

import logging
from typing import Any

from client.core.http_client import HttpClient

logger = logging.getLogger(__name__)

from PyQt6.QtCore import QObject, pyqtSignal


class _DocTypeEvents(QObject):
    """Общий канал: типы документов (список или поля) изменились."""

    types_changed = pyqtSignal()


doc_type_events = _DocTypeEvents()

class DocTypeService:
    """Сервис для управления типами документов"""

    def __init__(self, http_client: HttpClient):
        self.http = http_client
        self.base_path = "/doc-types"

    def get_all_types(self) -> list[dict[str, Any]]:
        """Получить все типы документов"""
        try:
            logger.info("📥 Запрос на получение типов документов...")

            # Пробуем отправить запрос с явными параметрами
            response = self.http.get(
                f"{self.base_path}",
                params={},  # Явно передаем пустые параметры
            )

            logger.info(f"📥 Получен ответ: {response}")
            if isinstance(response, list):
                return response
            return []
        except Exception as e:
            logger.exception(f"❌ Ошибка получения типов документов: {e}")
            import traceback

            traceback.print_exc()
            return []

    def get_type(self, type_id: int) -> dict[str, Any] | None:
        """Получить тип документа по ID"""
        try:
            return self.http.get(f"{self.base_path}/{type_id}")
        except Exception as e:
            logger.exception(f"Ошибка получения типа {type_id}: {e}")
            return None

    # client/services/doc_type_service.py

    def create_type(self, type_data: dict[str, Any]) -> dict[str, Any] | None:
        """Создать новый тип документа"""
        try:
            server_data = {
                "name": type_data.get("name", ""),
                "fields": type_data.get("fields", {}),
                "auto_num": type_data.get("auto_num", False),
                "smdo_code_type": type_data.get("smdo_code_type", ""),
            }

            response = self.http.post(f"{self.base_path}", json=server_data)
            logger.info(f"✅ Тип документа создан: {response}")
            if response:
                doc_type_events.types_changed.emit()
            return response
        except Exception as e:
            logger.exception(f"❌ Ошибка создания типа документа: {e}")
            return None

    def update_type(self, type_id: int, type_data: dict[str, Any]) -> dict[str, Any] | None:
        """Обновить тип документа"""
        try:
            server_data = {
                "name": type_data.get("name", ""),
                "fields": type_data.get("fields", {}),
                "auto_num": type_data.get("auto_num", False),
                "smdo_code_type": type_data.get("smdo_code_type", ""),
            }

            response = self.http.patch(f"{self.base_path}/{type_id}", json=server_data)
            logger.info(f"✅ Тип документа обновлен: {response}")
            if response:
                doc_type_events.types_changed.emit()
            return response
        except Exception as e:
            logger.exception(f"❌ Ошибка обновления типа {type_id}: {e}")
            return None

    def delete_type(self, type_id: int) -> bool:
        """Удалить тип документа"""
        try:
            self.http.delete(f"{self.base_path}/{type_id}")
            logger.info(f"✅ Тип документа {type_id} удален")
            doc_type_events.types_changed.emit()
            return True
        except Exception as e:
            logger.exception(f"❌ Ошибка удаления типа {type_id}: {e}")
            return False


# Синглтон
_doc_type_service_instance: DocTypeService | None = None


def get_doc_type_service(http_client: HttpClient) -> DocTypeService:
    """Получить экземпляр DocTypeService"""
    global _doc_type_service_instance
    if _doc_type_service_instance is None:
        _doc_type_service_instance = DocTypeService(http_client)
    return _doc_type_service_instance
