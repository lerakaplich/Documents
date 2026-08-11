from server.app.database.document_models import Document, AppRights, DocStatus, DocDirection
from server.app.repositories.document_repo import DocumentRepository
from server.app.schemas.doc.doc_employee_dto import ParticipantItem
from server.app.schemas.doc.document_dto import DocumentListItem, TagItem


class RegistryService:
    def __init__(self, db_repo: DocumentRepository):
        self.repo = db_repo

    async def get_all_paginated(
            self,
            user_id: int,
            user_rights: AppRights,
            scope: str = "my",
            is_completed: bool | None = None,
            status_filters: list | None = None,
            type_id: int | None = None,
            direction: str | None = None,
            tag_ids: list[int] | None = None,
            date_from: str | None = None,
            date_to: str | None = None,
            search: str | None = None,
            sort_by: str = "created_at",
            sort_order: str = "desc",
            limit: int = 20,
            offset: int = 0,
            **extra_params
    ) -> tuple[int, list[DocumentListItem]]:

        # Собираем словарь со всеми параметрами фильтрации
        filter_params = {
            "scope": scope,
            "is_completed": is_completed,
            "status_filters": status_filters,
            "type_id": type_id,
            "direction": direction,
            "tag_ids": tag_ids,
            "date_from": date_from,
            "date_to": date_to,
            "search": search,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "limit": limit,
            "offset": offset,
            **extra_params
        }

        # 1. Подготовка базового запроса
        query = self.repo.prepare_document_list_query()
        query = self.repo.apply_read_status(query, user_id)
        query = self.repo.apply_archive_status(query, user_id)
        query = self.repo.apply_pin_status(query, user_id)
        query = self.repo.apply_reply_status(query)
        query = self.repo.apply_attachments_status(query)

        # 2. Ограничение области видимости (scope) и прав доступа
        is_admin = user_rights in [AppRights.admin, AppRights.superadmin]

        if scope == "my" or not is_admin:
            # Для личного контура (или обычных пользователей) смотрим только документы с участием user_id
            query = self.repo.apply_user_scope(query, user_id, is_completed)
        else:
            # Для администраторов в глобальных scope ("all", "archive" и т.д.)
            query = self.repo.apply_admin_scope(query, is_completed)

        # 3. Бизнес-фильтры (передаем полный словарь фильтров в репозиторий)
        query = self.repo.apply_filters(query, filter_params)

        # 4. Полнотекстовый поиск
        if search and search.strip():
            for word in search.strip().split():
                query = self.repo.apply_search(query, f"%{word}%")

        # 5. Подсчет тотала (до лимита и оффсета)
        total = await self.repo.count_query(query)

        # 6. Сортировка и пагинация
        query = self.repo.apply_sorting(query, sort_by, sort_order)
        query = query.limit(limit).offset(offset)

        # 7. Выполнение запроса
        rows = await self.repo.execute_query(query)
        if not rows:
            rows = []

        # 8. Маппинг DTO
        items = []
        for doc, is_read, is_archived, is_pinned, reply_id, has_attachments in rows:
            item = DocumentListItem.model_validate(doc, from_attributes=True)

            item.is_read = is_read or False
            item.is_archived = is_archived or False
            item.is_pinned = is_pinned or False
            item.reply_id = reply_id
            item.has_attachments = has_attachments or False
            item.type_name = doc.type.name if doc.type else "Без типа"

            item.participants = [
                ParticipantItem(fio=self._format_fio(ed.employee), role=ed.role)
                for ed in doc.employees
            ]
            item.tags = [
                TagItem(name=tag.name, priority=tag.priority, color=tag.color)
                for tag in doc.tags
            ]

            items.append(item)

        return total, items

    def _format_fio(self, emp) -> str:
        """Форматирование ФИО вида: Фамилия И.О."""
        if not emp:
            return "Неизвестно"
        patronymic = f"{emp.patronymic[0]}." if emp.patronymic else ""
        return f"{emp.last_name} {emp.first_name[0]}.{patronymic}"