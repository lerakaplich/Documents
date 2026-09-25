# client/core/table/documents_panel_controller.py

from client.core.data.document_repository import document_repository
from client.core.data.document_data import DocumentDataConfig
from client.core.data.document_mapper import map_documents_response
from client.services.document_service import DocumentService


class DocumentsPanelController:
    """Контроллер состояния и загрузки данных для панели документов (Business Logic & State).

    ВАЖНО: список документов (load_all_documents / load_documents_by_type /
    load_documents_by_direction / search_documents / refresh) теперь идёт на
    реальный сервер через DocumentService + document_mapper.

    `document_repository` оставлен и используется ТОЛЬКО для метаданных типов
    документов (список полей типа для доп. колонок в table_controller) — эти
    данные пока тестовые (DocumentDataConfig.DOCUMENT_TYPES), но карточки
    самих документов уже настоящие. Как только типы документов тоже будут
    приходить с сервера (например, через doc_type_service.py), репозиторий
    можно убрать полностью.

    Методы редактирования/удаления/истории/комментариев/перенаправления ниже
    ПОКА не переведены на реальный API (это следующий шаг — им нужны схемы
    DocumentDetailRead/AdminMetadataUpdate и т.д.). Сейчас они по-прежнему
    обращаются к фейковому репозиторию и с реальными ID документов просто
    ничего не найдут, откатываясь на переданные им данные без ошибок —
    поэтому окно не падает, но, например, "Сохранить" в редактировании
    документа не отправит изменения на сервер.
    """

    def __init__(self, http_client):
        self.service = DocumentService(http_client)
        self.repository = document_repository  # только для метаданных типов, см. докстринг

        # Единственный источник правды для состояния панели
        self.current_type_id = None
        self.current_direction = None
        self.current_query = ""
        self.current_title = "Все документы"
        self.current_view_mode = "all"

    # ========== ЗАГРУЗКА СПИСКА ДОКУМЕНТОВ (реальный API) ==========

    def load_all_documents(self):
        """Загружает все документы, обновляет состояние."""
        response = self.service.get_documents(scope="all")
        documents = map_documents_response(response)

        self.current_type_id = None
        self.current_direction = None
        self.current_title = "Все документы"
        self.current_view_mode = "all"
        return documents, self.current_title, self.current_view_mode, "default"

    def load_documents_by_type(self, type_id: int, title: str = None):
        """Загружает документы по типу, обновляет состояние.

        `title` — имя типа, если оно уже известно вызывающей стороне (например,
        LeftPanel передаёт его вместе с type_id в сигнале type_clicked). Если не
        передано, используем f"Тип {type_id}" — специального запроса за именем
        типа отсюда не делаем.
        """
        response = self.service.get_documents(scope="all", type_id=type_id)
        documents = map_documents_response(response)

        self.current_type_id = type_id
        self.current_direction = None
        self.current_view_mode = "type"
        self.current_title = title or f"Тип {type_id}"

        return documents, self.current_title, "type", str(type_id)

    def load_documents_by_direction(self, direction: str, title: str = None):
        """Загружает документы по направлению (internal/external)."""
        response = self.service.get_documents(scope="all", direction=direction)
        documents = map_documents_response(response)

        self.current_direction = direction
        self.current_type_id = None
        self.current_view_mode = "direction"

        if title is None:
            title = DocumentDataConfig.DIRECTION_MAPPING.get(direction, direction)
        self.current_title = title

        doc_type = direction if direction in ["incoming", "outgoing", "internal"] else "default"
        return documents, title, "direction", doc_type

    def search_documents(self, query: str):
        """Поиск документов по строке через сервер. Изменяет состояние поиска."""
        self.current_query = query
        if query and len(query) >= 3:
            response = self.service.get_documents(scope="all", search=query)
            results = map_documents_response(response)
            return results, f"Поиск: {query}", "search", "default"
        else:
            # Короткий запрос — возвращаем всё в рамках текущего режима
            return self.refresh()

    def refresh(self):
        """Обновляет данные в соответствии с текущим состоянием."""
        if self.current_type_id is not None:
            return self.load_documents_by_type(self.current_type_id, self.current_title)
        elif self.current_direction is not None:
            return self.load_documents_by_direction(self.current_direction, self.current_title)
        else:
            return self.load_all_documents()

    # ========== ОСТАЛЬНАЯ БИЗНЕС-ЛОГИКА (пока на фейковых данных — см. докстринг класса) ==========

    def get_full_document_for_history(self, document_data: dict) -> dict:
        """
        Получает полные данные документа с историей

        Args:
            document_data: базовые данные документа

        Returns:
            dict: обогащенные данные
        """
        try:
            doc_id = document_data.get('id')
            if not doc_id:
                return document_data

            full_doc = self.repository.get_document_by_id(doc_id)
            if full_doc:
                full_doc['history'] = self.get_document_history(doc_id)
                return full_doc
        except Exception as e:
            print(f"[Controller] Error getting full document for history: {e}")

        return document_data

    def get_document_history(self, document_id: int) -> list:
        """
        Получает историю документа

        Args:
            document_id: ID документа

        Returns:
            list: список событий истории
        """
        try:
            # TODO: подключить GET /documents/{document_id}/history (уже есть на сервере)
            return []
        except Exception as e:
            print(f"[Controller] Error getting document history: {e}")
            return []

    def get_current_user(self) -> dict:
        """Возвращает текущего пользователя"""
        # TODO: брать из AppState().current_user вместо заглушки
        return {
            'id': 1,
            'full_name': 'Иванов И.И.'
        }

    def get_employees_for_redirect(self) -> list:
        """Возвращает список сотрудников для перенаправления (логика контроллера)"""
        return [
            {"id": 1, "name": "Иванов И.И."},
            {"id": 2, "name": "Петров П.П."},
            {"id": 3, "name": "Морозов М.М."},
            {"id": 4, "name": "Сидоров С.С."}
        ]

    def redirect_document(self, document_id: int, recipient_ids: list, comment: str) -> bool:
        """Бизнес-логика выполнения перенаправления документа"""
        print(f"[Controller] Redirecting doc {document_id} to {recipient_ids} with comment: {comment}")
        return True

    def get_full_document_for_comment(self, document_data: dict) -> dict:
        """Готовит полную информацию о документе для диалога комментариев"""
        doc_id = document_data.get("id")
        full_doc = DocumentDataConfig.get_document_by_id(doc_id)

        if full_doc:
            document_to_pass = full_doc.copy()
        else:
            document_to_pass = document_data.copy()

        if "reg_number" in document_to_pass and "number" not in document_to_pass:
            document_to_pass["number"] = document_to_pass.get("reg_number", "")
        if "title" in document_to_pass and "subject" not in document_to_pass:
            document_to_pass["subject"] = document_to_pass.get("title", "")

        return document_to_pass

    def add_comment_to_document(self, document_id: int, new_comment: dict) -> bool:
        """Сохранение комментария к документу"""
        try:
            doc = DocumentDataConfig.get_document_by_id(document_id)
            if doc:
                if 'comments' not in doc:
                    doc['comments'] = []
                doc['comments'].append(new_comment)
                doc['last_comment_text'] = new_comment.get('text', '')
                return True
        except Exception as e:
            print(f"[Controller] Error saving comment: {e}")
        return False

    def get_full_document_for_edit(self, document_data: dict) -> dict:
        """
        Получает полные данные документа для редактирования

        Args:
            document_data: базовые данные документа

        Returns:
            dict: обогащенные данные
        """
        try:
            doc_id = document_data.get('id')
            if not doc_id:
                return document_data

            full_doc = self.repository.get_document_by_id(doc_id)
            if full_doc:
                return full_doc
        except Exception as e:
            print(f"[Controller] Error getting full document for edit: {e}")

        return document_data

    def update_document(self, document_data: dict) -> bool:
        """
        Обновляет документ

        Args:
            document_data: обновленные данные документа

        Returns:
            bool: успех операции
        """
        try:
            doc_id = document_data.get('id')
            if not doc_id:
                return False

            return self.repository.update_document(doc_id, document_data)
        except Exception as e:
            print(f"[Controller] Error updating document: {e}")
            return False

    def delete_document(self, document_id: int) -> bool:
        """Удаляет документ"""
        try:
            doc = self.repository.get_document_by_id(document_id)
            if doc:
                self.repository._documents = [d for d in self.repository._documents if d.get('id') != document_id]
                return True
            return False
        except Exception as e:
            print(f"[Controller] Error deleting document: {e}")
            return False