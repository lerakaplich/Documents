# client/core/data/document_repository.py
"""
Репозиторий для работы с документами - ЕДИНЫЙ ИСТОЧНИК ДАННЫХ
"""
from typing import List, Dict, Any, Optional
from client.core.data.document_data import DocumentDataConfig


class DocumentRepository:
    """
    Репозиторий для работы с документами.
    Singleton - единый источник данных для всего приложения.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._documents = DocumentDataConfig.TEST_DATA.copy()
            self._document_types = DocumentDataConfig.DOCUMENT_TYPES.copy()
            self._current_type_id = None  # Текущий выбранный тип
            self._initialized = True
            print("[DocumentRepository] Инициализирован")

    # ========== ДОКУМЕНТЫ ==========

    def get_all_documents(self) -> List[Dict[str, Any]]:
        """Получить все документы"""
        return self._documents.copy()

    def get_documents_by_type(self, type_id: int) -> List[Dict[str, Any]]:
        """Получить документы по типу"""
        return [doc for doc in self._documents if doc.get('type_id') == type_id]

    def get_documents_by_direction(self, direction: str) -> List[Dict[str, Any]]:
        """Получить документы по направлению"""
        return [doc for doc in self._documents if doc.get('direction') == direction]

    def get_document_by_id(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Получить документ по ID"""
        for doc in self._documents:
            if doc.get('id') == doc_id:
                return doc.copy()
        return None

    def search_documents(self, query: str) -> List[Dict[str, Any]]:
        """Поиск документов"""
        if not query or len(query) < 3:
            return self._documents.copy()

        query_lower = query.lower()
        results = []

        for doc in self._documents:
            searchable_fields = ['title', 'reg_number', 'about', 'type_name']
            for field in searchable_fields:
                value = doc.get(field, '')
                if query_lower in str(value).lower():
                    results.append(doc)
                    break

        return results

    def update_document(self, doc_id: int, data: Dict[str, Any]) -> bool:
        """Обновить документ"""
        for i, doc in enumerate(self._documents):
            if doc.get('id') == doc_id:
                self._documents[i].update(data)
                return True
        return False

    # ========== ТИПЫ ДОКУМЕНТОВ ==========

    def get_document_types(self) -> List[Dict[str, Any]]:
        """Получить все типы документов"""
        return self._document_types.copy()

    def get_document_type_by_id(self, type_id: int) -> Optional[Dict[str, Any]]:
        """Получить тип документа по ID"""
        for doc_type in self._document_types:
            if doc_type.get('id') == type_id:
                return doc_type.copy()
        return None

    def get_types_by_direction(self, direction: str) -> List[Dict[str, Any]]:
        """Получить типы документов по направлению"""
        type_ids = DocumentDataConfig.TYPE_DIRECTION_MAPPING.get(direction, [])
        return [t for t in self._document_types if t.get('id') in type_ids]

    def get_current_type_id(self) -> Optional[int]:
        """Получить текущий выбранный тип"""
        return self._current_type_id

    def set_current_type_id(self, type_id: Optional[int]):
        """Установить текущий выбранный тип"""
        self._current_type_id = type_id

    # ========== ДЛЯ ЛЕВОЙ ПАНЕЛИ ==========

    def get_directions_data(self) -> List[Dict[str, Any]]:
        """Получить данные для левой панели"""
        return DocumentDataConfig.get_directions_data()

    # ========== КОЛОНКИ ==========

    # client/core/data/document_repository.py

    def get_columns_for_type(self, type_id: int) -> Dict[int, str]:
        """Получить конфигурацию колонок для типа"""
        return DocumentDataConfig.get_columns_for_type(type_id)

    def get_default_columns(self) -> Dict[int, str]:
        """Получить стандартные колонки"""
        return DocumentDataConfig.COLUMNS_CONFIG.copy()

    def get_type_name_for_columns(self, type_id: int) -> str:
        """
        Получить имя типа для сохранения настроек колонок.
        Используется как ключ в SettingsManager.
        """
        if type_id is None:
            return "default"

        type_info = self.get_document_type_by_id(type_id)
        if type_info:
            # Используем имя типа как ключ, но заменяем пробелы и спецсимволы
            name = type_info.get('name', f"type_{type_id}")
            # Транслитерация или замена пробелов
            return name.replace(' ', '_').replace('(', '').replace(')', '')
        return f"type_{type_id}"


# Глобальный экземпляр (Singleton)
document_repository = DocumentRepository()