# client/core/table/documents_panel_controller.py

import math

from client.core.data.document_data import DocumentDataConfig
from client.core.data.document_mapper import map_documents_response
from client.core.data.document_repository import document_repository
from client.core.settings.settings_keys import SettingsKeys
from client.core.settings.settings_manager import SettingsManager
from client.services.doc_type_service import get_doc_type_service
from client.services.document_service import DocumentService

PAGE_SIZE = 50

# Заголовок столбца → значение sort_by для GET /documents/documents/.
# Столбцы, которых здесь нет (списки, теги, вложения…), не сортируются.
# ⚠ Swagger не перечисляет допустимые значения sort_by — проверьте каждое
# в Swagger и уберите те, что сервер не принимает.
SORT_FIELDS = {
    "Номер документа": "reg_number",
    "Тема": "title",
    "Дата создания": "created_at",
    "Статус": "status",
    "Срок исполнения": "deadline",
    "Краткое содержание": "about",
    "Направление": "direction",
}


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

        # Фильтры из меню «Фильтр»/«Статусы» — применяются на сервере и
        # сохраняются при переходе между типами/направлениями.
        self.filters = {
            "scope": "all",
            "is_completed": None,
            "is_archived": None,
            "status_filters": [],
            "date_from": None,
            "date_to": None,
            "tag_ids": [],
        }

        # Пагинация: сервер отдаёт total/limit/offset, лимит ≤ 100
        self.page_size = PAGE_SIZE
        self.current_page = 1
        self.pagination = {"page": 1, "pages": 1, "total": 0}
        # Сортировка (по умолчанию как на сервере: новые сверху)
        self.sort_by = "created_at"
        self.sort_order = "desc"

        self.doc_type_service = get_doc_type_service(http_client)
        self._doc_types: list[dict] = []

    # ========== ТИПЫ ДОКУМЕНТОВ (для диалога создания) ==========

    def refresh_doc_types(self) -> list[dict]:
        """Перезагружает типы с сервером (id, name, fields, ...). Если запрос
        не удался (сервис вернёт []), остаётся прежний кэш."""
        types = self.doc_type_service.get_all_types()
        if types:
            self._doc_types = types
        return self._doc_types

    def get_document_types(self) -> list[dict]:
        return self._doc_types or self.refresh_doc_types()

    # ========== ЗАГРУЗКА СПИСКА ДОКУМЕНТОВ (реальный API, постранично) ==========

    def _fetch(self, page: int, **filters) -> list:
        """Запрашивает одну страницу, обновляет self.pagination / self.current_page."""
        page = max(1, page)

        params = dict(filters)
        params.update(self._filter_params())
        params["sort_by"] = self.sort_by
        params["sort_order"] = self.sort_order

        def _request(p):
            return self.service.get_documents(
                limit=self.page_size,
                offset=(p - 1) * self.page_size,
                **params,
            )

        response = _request(page)
        total = int(response.get("total", 0) or 0)
        pages = max(1, math.ceil(total / self.page_size))

        # Страницы больше нет (например, удалили последний документ на ней) —
        # переходим на последнюю существующую.
        if page > pages:
            page = pages
            response = _request(page)

        self.current_page = page
        self.pagination = {"page": page, "pages": pages, "total": total}

        documents = map_documents_response(response)
        # Сервер уже отфильтровал по is_archived, поэтому флаг известен точно
        is_archive_view = params["is_archived"]
        for d in documents:
            d["is_archived"] = is_archive_view
        return documents

    def _filter_params(self) -> dict:
        """Архивные документы видны ТОЛЬКО в режиме архива, везде больше скрыты."""
        f = self.filters
        archive_mode = self.current_view_mode == "archive"

        scope = "archive" if archive_mode else f["scope"]
        if not archive_mode and scope == "archive":
            scope = "all"

        params = {"scope": scope, "is_archived": archive_mode}
        if f["is_completed"] is not None:
            params["is_completed"] = f["is_completed"]
        if f["status_filters"]:
            params["status_filters"] = list(f["status_filters"])
        if f["date_from"]:
            params["date_from"] = f["date_from"]
        if f["date_to"]:
            params["date_to"] = f["date_to"]
        if f.get("tag_ids"):
            params["tag_ids"] = list(f["tag_ids"])[:5]  # максимум 5 тегов
        return params

    def set_filters(
        self,
        scope: str = "all",
        is_completed=None,
        status_filters=None,
        date_from=None,
        date_to=None,
        is_archived=None,
        tag_ids=None,
    ):
        """is_archived оставлен в сигнатуре для совместимости и игнорируется:
        архив определяется режимом просмотра (current_view_mode)."""
        self.filters = {
            "scope": scope or "all",
            "is_completed": is_completed,
            "status_filters": list(status_filters or []),
            "date_from": date_from,
            "date_to": date_to,
            "tag_ids": list(tag_ids or []),
        }
        return self._load_current(1)

    def _search_active(self) -> bool:
        return bool(self.current_query) and len(self.current_query) >= 3

    def settings_key(self) -> str:
        """Ключ локальных настроек таблицы (ширины, высоты строк, закрепления,
        порядок строк). Свой у каждого вида:
        «Все документы» → default, «Все типы» → external / internal,
        тип → его id, архив → archive, поиск → search."""
        if self._search_active():
            return "search"
        if self.current_view_mode == "archive":
            return "archive"
        if self.current_type_id is not None:
            return str(self.current_type_id)
        if self.current_direction is not None:
            return self.current_direction
        return "default"

    def _load_current(self, page: int):
        """Загружает страницу текущего режима.
        Приоритет: поиск > архив > тип > направление > все.
        Возвращает (documents, title, view_mode, doc_type), где doc_type — ключ
        настроек вида (см. settings_key)."""
        key = self.settings_key()

        if self._search_active():
            documents = self._fetch(page, search=self.current_query)
            return documents, f"Поиск: {self.current_query}", "search", key

        if self.current_view_mode == "archive":
            documents = self._fetch(page)
            return documents, self.current_title, "archive", key

        if self.current_type_id is not None:
            documents = self._fetch(page, type_id=self.current_type_id, direction=self.current_direction)
            return documents, self.current_title, "type", key

        if self.current_direction is not None:
            documents = self._fetch(page, direction=self.current_direction)
            return documents, self.current_title, "direction", key

        documents = self._fetch(page)
        return documents, self.current_title, "all", key

    def toggle_sort(self, column_title: str):
        """Клик по заголовку: тот же столбец — меняем направление, другой —
        сортируем по возрастанию. Возвращает то же, что _load_current, либо
        None, если по этому столбцу сортировка не поддерживается."""
        field = SORT_FIELDS.get(column_title)
        if field is None:
            return None

        # Ручной порядок строк (перетаскивание) не должен перебивать новую сортировку
        SettingsManager().set_row_order_by_type([], self.settings_key())

        if self.sort_by == field:
            self.sort_order = "asc" if self.sort_order == "desc" else "desc"
        else:
            self.sort_by = field
            self.sort_order = "asc"
        return self._load_current(1)

    def load_all_documents(self):
        self.filters["scope"] = "all"
        self.current_type_id = None
        self.current_direction = None
        self.current_query = ""
        self.current_title = "Все документы"
        self.current_view_mode = "all"
        return self._load_current(1)

    def load_documents_by_type(self, type_id: int, title: str | None = None, direction: str | None = None):
        # Типы с полями при переходе на вкладку подгружает панель в фоне
        # (DocumentsPanel.load_documents_by_type) — отдельный GET здесь задерживал каждую вкладку.
        # Если кэш пуст, get_document_types() всё равно загрузит их сам.
        self.filters["scope"] = "all"
        self.filters["is_archived"] = None  # ← НОВОЕ
        self.current_type_id = type_id
        self.current_direction = direction
        self.current_query = ""
        self.current_view_mode = "type"
        self.current_title = title or f"Тип {type_id}"
        return self._load_current(1)

    def load_documents_by_direction(self, direction: str, title: str | None = None):
        self.filters["scope"] = "all"  # ← НОВОЕ
        self.filters["is_archived"] = None  # ← НОВОЕ
        self.current_direction = direction
        self.current_type_id = None
        self.current_query = ""
        self.current_view_mode = "direction"
        if title is None:
            title = DocumentDataConfig.DIRECTION_MAPPING.get(direction, direction)
        self.current_title = title
        return self._load_current(1)

    def load_archived_documents(self):
        """Загружает персональный архив текущего пользователя (scope='archive')."""
        self.filters["scope"] = "archive"
        self.filters["is_archived"] = True
        self.current_type_id = None
        self.current_direction = None
        self.current_query = ""
        self.current_title = "Архив"
        self.current_view_mode = "archive"
        return self._load_current(1)

    def search_documents(self, query: str):
        """Поиск через сервер (страница 1). Короткий запрос (<3 символов) —
        возврат к текущему режиму просмотра."""
        self.current_query = query or ""
        return self._load_current(1)

    def change_page(self, delta: int):
        """Перейти на страницу current_page + delta в рамках текущего режима."""
        new_page = min(max(1, self.current_page + delta), self.pagination["pages"])
        return self._load_current(new_page)

    def refresh(self):
        """Перезагружает ТЕКУЩУЮ страницу текущего режима."""
        return self._load_current(self.current_page)

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
            doc_id = document_data.get("id")
            if not doc_id:
                return document_data

            full_doc = self.repository.get_document_by_id(doc_id)
            if full_doc:
                full_doc["history"] = self.get_document_history(doc_id)
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
        return {"id": 1, "full_name": "Иванов И.И."}

    def get_employees_for_redirect(self) -> list:
        """Возвращает список сотрудников для перенаправления (логика контроллера)"""
        return [
            {"id": 1, "name": "Иванов И.И."},
            {"id": 2, "name": "Петров П.П."},
            {"id": 3, "name": "Морозов М.М."},
            {"id": 4, "name": "Сидоров С.С."},
        ]

    def redirect_document(self, document_id: int, recipient_ids: list, comment: str) -> bool:
        """Бизнес-логика выполнения перенаправления документа"""
        print(f"[Controller] Redirecting doc {document_id} to {recipient_ids} with comment: {comment}")
        return True

    def archive_document(self, document_id: int) -> bool:
        """Архивирует документ для текущего пользователя."""
        try:
            self.service.archive_document(document_id)
            return True
        except Exception as e:
            print(f"[Controller] Error archiving document {document_id}: {e}")
            return False

    def unarchive_document(self, document_id: int) -> bool:
        """Разархивирует документ для текущего пользователя."""
        try:
            self.service.unarchive_document(document_id)
            return True
        except Exception as e:
            print(f"[Controller] Error unarchiving document {document_id}: {e}")
            return False

    def get_full_document_for_comment(self, document_data: dict) -> dict:
        """Готовит полную информацию о документе для диалога комментариев"""
        doc_id = document_data.get("id")
        full_doc = DocumentDataConfig.get_document_by_id(doc_id)

        document_to_pass = full_doc.copy() if full_doc else document_data.copy()

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
                if "comments" not in doc:
                    doc["comments"] = []
                doc["comments"].append(new_comment)
                doc["last_comment_text"] = new_comment.get("text", "")
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
            doc_id = document_data.get("id")
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
            doc_id = document_data.get("id")
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
                self.repository._documents = [d for d in self.repository._documents if d.get("id") != document_id]
                return True
            return False
        except Exception as e:
            print(f"[Controller] Error deleting document: {e}")
            return False