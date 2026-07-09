from client.core.data.document_repository import document_repository
from client.core.data.document_data import DocumentDataConfig

class DocumentsPanelController:
    """Контроллер состояния и загрузки данных для панели документов."""
    def __init__(self):
        self.repository = document_repository
        self.current_type_id = None
        self.current_direction = None
        self.current_query = ""
        self.current_title = "Все документы"
        self.current_view_mode = "all"

    def load_all_documents(self):
        """Загружает все документы, обновляет состояние."""
        documents = self.repository.get_all_documents()
        self.current_type_id = None
        self.current_direction = None
        self.current_title = "Все документы"
        self.current_view_mode = "all"
        return documents, self.current_title, self.current_view_mode, "default"

    def load_documents_by_type(self, type_id: int):
        """Загружает документы по типу, обновляет состояние."""
        documents = self.repository.get_documents_by_type(type_id)
        self.current_type_id = type_id
        self.current_direction = None
        self.current_view_mode = "type"

        type_info = self.repository.get_document_type_by_id(type_id)
        title = type_info.get('name', f"Тип {type_id}") if type_info else f"Тип {type_id}"
        self.current_title = title

        return documents, title, "type", str(type_id)

    def load_documents_by_direction(self, direction: str, title: str = None):
        """Загружает документы по направлению (входящие/исходящие/внутренние)."""
        documents = self.repository.get_documents_by_direction(direction)
        self.current_direction = direction
        self.current_type_id = None
        self.current_view_mode = "direction"

        if title is None:
            title = DocumentDataConfig.DIRECTION_MAPPING.get(direction, direction)
        self.current_title = title

        doc_type = direction if direction in ["incoming", "outgoing", "internal"] else "default"
        return documents, title, "direction", doc_type

    def search_documents(self, query: str):
        """Поиск документов по строке. Возвращает результат и флаг поиска."""
        self.current_query = query
        if query and len(query) >= 3:
            results = self.repository.search_documents(query)
            return results, f"Поиск: {query}", "search", "default"
        else:
            # Если запрос короткий, возвращаем всё, но не меняем view_mode
            return self.repository.get_all_documents(), self.current_title, self.current_view_mode, "default"

    def refresh(self):
        """Обновляет данные в соответствии с текущим состоянием."""
        if self.current_type_id is not None:
            return self.load_documents_by_type(self.current_type_id)
        elif self.current_direction is not None:
            return self.load_documents_by_direction(self.current_direction)
        else:
            return self.load_all_documents()