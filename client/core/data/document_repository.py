# client/core/data/document_repository.py
from typing import List, Dict, Any, Optional
from client.core.data.document_data import DocumentDataConfig
from client.services.document_service import DocumentService


class DocumentRepository:
    """Репозиторий документов - единый источник данных"""

    def __init__(self):
        self._documents: List[Dict[str, Any]] = []
        self._document_types = DocumentDataConfig.DOCUMENT_TYPES
        self._service: Optional[DocumentService] = None
        self._initialized = False

    def set_service(self, service: DocumentService):
        """Установить сервис для работы с API"""
        self._service = service
        print("✅ DocumentService установлен в DocumentRepository")

    def initialize(self):
        """Инициализация репозитория"""
        if self._initialized:
            return

        if self._service:
            # Загружаем данные с сервера
            self._documents = self._service.get_all_documents()
            print(f"📥 Загружено {len(self._documents)} документов с сервера")
        else:
            # Используем тестовые данные
            self._documents = DocumentDataConfig._initialize_test_data()
            print(f"📥 Используются тестовые данные: {len(self._documents)} документов")

        self._initialized = True

    def refresh(self):
        """Обновить данные из API"""
        if self._service:
            self._documents = self._service.get_all_documents()
            print(f"🔄 Обновлено: {len(self._documents)} документов")
        return self._documents

    # ============ ПОЛУЧЕНИЕ ДАННЫХ ============

    def get_all_documents(self) -> List[Dict[str, Any]]:
        """Получить все документы"""
        if not self._initialized:
            self.initialize()
        return self._documents.copy()

    def get_document_by_id(self, doc_id: int) -> Optional[Dict[str, Any]]:
        """Получить документ по ID"""
        for doc in self._documents:
            if doc.get('id') == doc_id:
                return doc
        return None

    def get_documents_by_type(self, type_id: int) -> List[Dict[str, Any]]:
        """Получить документы по типу"""
        if self._service:
            return self._service.get_documents_by_type(type_id)
        return [doc for doc in self._documents if doc.get('type_id') == type_id]

    def get_documents_by_direction(self, direction: str) -> List[Dict[str, Any]]:
        """Получить документы по направлению"""
        if self._service:
            return self._service.get_documents_by_direction(direction)
        return [doc for doc in self._documents if doc.get('direction') == direction]

    def search_documents(self, query: str) -> List[Dict[str, Any]]:
        """Поиск документов"""
        query_lower = query.lower()
        results = []
        for doc in self._documents:
            if (query_lower in str(doc.get('title', '')).lower() or
                    query_lower in str(doc.get('about', '')).lower() or
                    query_lower in str(doc.get('reg_number', '')).lower()):
                results.append(doc)
        return results

    def get_document_type_by_id(self, type_id: int) -> Optional[Dict[str, Any]]:
        """Получить тип документа по ID"""
        for doc_type in self._document_types:
            if doc_type.get('id') == type_id:
                return doc_type
        return None

    def get_document_types(self) -> List[Dict[str, Any]]:
        """Получить все типы документов"""
        return self._document_types.copy()

    # ============ УПРАВЛЕНИЕ ДОКУМЕНТАМИ ============

    def create_document(self, document_data: Dict[str, Any]) -> bool:
        """Создать документ"""
        if self._service:
            try:
                result = self._service.create_document(document_data)
                if result:
                    self._documents.append(result)
                    return True
            except Exception as e:
                print(f"❌ Ошибка создания документа: {e}")
                return False
        else:
            # Локальное создание
            new_doc = document_data.copy()
            new_doc['id'] = max([d.get('id', 0) for d in self._documents] + [0]) + 1
            if 'created_at' not in new_doc:
                from datetime import datetime
                new_doc['created_at'] = datetime.now().isoformat()
            self._documents.append(new_doc)
            return True

    def update_document(self, doc_id: int, document_data: Dict[str, Any]) -> bool:
        """Обновить документ"""
        if self._service:
            try:
                result = self._service.update_document(doc_id, document_data)
                if result:
                    # Обновляем локальный кэш
                    for i, doc in enumerate(self._documents):
                        if doc.get('id') == doc_id:
                            self._documents[i] = result
                            break
                    return True
            except Exception as e:
                print(f"❌ Ошибка обновления документа: {e}")
                return False
        else:
            # Локальное обновление
            for i, doc in enumerate(self._documents):
                if doc.get('id') == doc_id:
                    self._documents[i].update(document_data)
                    return True
            return False

    def delete_document(self, doc_id: int) -> bool:
        """Удалить документ"""
        if self._service:
            try:
                success = self._service.delete_document(doc_id)
                if success:
                    self._documents = [d for d in self._documents if d.get('id') != doc_id]
                return success
            except Exception as e:
                print(f"❌ Ошибка удаления документа: {e}")
                return False
        else:
            # Локальное удаление
            for i, doc in enumerate(self._documents):
                if doc.get('id') == doc_id:
                    self._documents.pop(i)
                    return True
            return False

    def mark_documents_as_read(self, doc_ids: List[int]) -> int:
        """Отметить документы как прочитанные"""
        if self._service:
            try:
                result = self._service.mark_as_read(doc_ids)
                return result.get('marked_count', 0)
            except Exception as e:
                print(f"❌ Ошибка отметки о прочтении: {e}")
                return 0
        return 0


# Создаем глобальный экземпляр
document_repository = DocumentRepository()