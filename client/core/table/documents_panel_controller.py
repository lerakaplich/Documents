# client/core/table/documents_panel_controller.py

from client.core.data.document_repository import document_repository
from client.core.data.document_data import DocumentDataConfig


class DocumentsPanelController:
    """Контроллер состояния и загрузки данных для панели документов (Business Logic & State)."""

    def __init__(self):
        self.repository = document_repository

        # Единственный источник правды для состояния панели
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
        """Загружает документы по направлению."""
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
        """Поиск документов по строке. Изменяет состояние поиска."""
        self.current_query = query
        if query and len(query) >= 3:
            results = self.repository.search_documents(query)
            return results, f"Поиск: {query}", "search", "default"
        else:
            # Если запрос короткий, возвращаем всё в рамках текущего режима
            return self.repository.get_all_documents(), self.current_title, self.current_view_mode, "default"

    def refresh(self):
        """Обновляет данные в соответствии с текущим состоянием."""
        if self.current_type_id is not None:
            return self.load_documents_by_type(self.current_type_id)
        elif self.current_direction is not None:
            return self.load_documents_by_direction(self.current_direction)
        else:
            return self.load_all_documents()

    # ========== ПЕРЕНЕСЕННАЯ БИЗНЕС-ЛОГИКА ИЗ VIEW ==========

    def get_employees_for_redirect(self) -> list:
        """Возвращает список сотрудников для перенаправления (логика контроллера)"""
        # В будущем этот метод будет делать запрос в репозиторий или БД
        return [
            {"id": 1, "name": "Иванов И.И."},
            {"id": 2, "name": "Петров П.П."},
            {"id": 3, "name": "Морозов М.М."},
            {"id": 4, "name": "Сидоров С.С."}
        ]

    def redirect_document(self, document_id: int, recipient_ids: list, comment: str) -> bool:
        """Бизнес-логика выполнения перенаправления документа"""
        # Имитируем успешное выполнение операции в репозитории/БД
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

        # Нормализация полей под структуру CommentDialog
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

    def get_current_user(self) -> dict:
        """Возвращает текущего авторизованного пользователя"""
        # Логику получения текущего сессионного юзера держим здесь
        return {
            'id': 2,
            'full_name': 'Сидоров С.С.',
            'last_name': 'Сидоров',
            'first_name': 'Сергей',
            'middle_name': 'Сергеевич'
        }