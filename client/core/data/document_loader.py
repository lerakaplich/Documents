# core/data/document_loader.py
"""
Загрузчик документов - бизнес-логика загрузки
"""

from collections.abc import Callable

from client.core.data.document_repository import document_repository


class DocumentLoader:
    """
    Отвечает за загрузку документов с различными фильтрами.
    Не содержит UI-кода.
    """

    def __init__(self, repository=None):
        self.repository = repository or document_repository
        self._listeners: list[Callable] = []

    def load_all(self) -> list[dict]:
        """Загрузить все документы"""
        return self.repository.get_all_documents()

    def load_by_type(self, type_id: int) -> list[dict]:
        """Загрузить документы по типу"""
        return self.repository.get_documents_by_type(type_id)

    def load_by_direction(self, direction: str) -> list[dict]:
        """Загрузить документы по направлению"""
        return self.repository.get_documents_by_direction(direction)

    def load_by_search(self, query: str) -> list[dict]:
        """Загрузить документы по поисковому запросу"""
        return self.repository.search_documents(query)

    def load_by_filter(self, filters: dict) -> list[dict]:
        """Загрузить документы с применением фильтров"""
        documents = self.repository.get_all_documents()

        # Применяем фильтры
        if "type_id" in filters:
            documents = [d for d in documents if d.get("type_id") == filters["type_id"]]

        if "direction" in filters:
            documents = [d for d in documents if d.get("direction") == filters["direction"]]

        if "read_status" in filters:
            is_read = filters["read_status"]
            documents = [d for d in documents if d.get("is_read", False) == is_read]

        if filters.get("query"):
            query = filters["query"].lower()
            documents = [
                d
                for d in documents
                if query in str(d.get("subject", "")).lower() or query in str(d.get("document_number", "")).lower()
            ]

        return documents

    def get_type_info(self, type_id: int) -> dict | None:
        """Получить информацию о типе документа"""
        return self.repository.get_document_type_by_id(type_id)

    def get_direction_title(self, direction: str) -> str:
        """Получить название направления"""
        from client.core.data.document_data import DocumentDataConfig

        return DocumentDataConfig.DIRECTION_MAPPING.get(direction, direction)

    def add_listener(self, callback: Callable):
        """Добавить слушатель загрузки"""
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable):
        """Удалить слушатель"""
        if callback in self._listeners:
            self._listeners.remove(callback)

    def _notify_listeners(self, documents: list[dict]):
        """Уведомить слушателей о загрузке"""
        for listener in self._listeners:
            try:
                listener(documents)
            except Exception as e:
                print(f"[DocumentLoader] Error in listener: {e}")
