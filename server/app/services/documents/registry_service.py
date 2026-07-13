from typing import List, Optional, Tuple
from datetime import date
from server.app.database.document_models import Document, AppRights, DocStatus, DocDirection
from server.app.repositories.document_repo import DocumentRepository
from server.app.schemas.doc.doc_employee_dto import ParticipantItem
from server.app.schemas.doc.document_dto import DocumentListItem, TagItem


class RegistryService:
    def __init__(self, db_repo: DocumentRepository):
        self.repo = db_repo

    async def get_all_paginated(self, user_id: int, user_rights: AppRights, **params) -> Tuple[int, List[Document]]:
        # 1. Начало сборки запроса
        query = self.repo.prepare_document_list_query()
        query = self.repo.apply_read_status(query, user_id)
        query = self.repo.apply_archive_status(query, user_id)
        query = self.repo.apply_pin_status(query, user_id)
        query = self.repo.apply_reply_status(query)
        query = self.repo.apply_attachments_status(query)


        # 2. Применяем права доступа
        if user_rights not in [AppRights.admin, AppRights.superadmin]:
            query = self.repo.apply_user_scope(query, user_id, params.get('is_completed'))
        elif params.get('is_completed') is not None:
            query = self.repo.apply_admin_scope(query, params['is_completed'])

        # 3. Применяем бизнес-фильтры
        query = self.repo.apply_filters(query, params)

        # 4. Полнотекстовый поиск (логику разбиения слов оставляем в сервисе)
        search = params.get('search')
        if search and search.strip():
            for word in search.strip().split():
                query = self.repo.apply_search(query, f"%{word}%")

        # 5. Считаем общее количество (до пагинации)
        total = await self.repo.count_query(query)

        # 6. Сортировка и пагинация
        query = self.repo.apply_sorting(
            query,
            params.get('sort_by', 'created_at'),
            params.get('sort_order', 'desc')
        )
        query = query.limit(params.get('limit', 20)).offset(params.get('offset', 0))

        # 7. Выполнение
        rows = await self.repo.execute_query(query)

        if rows is None:
            rows = []

        items = []
        for doc, is_read, is_archived, is_pinned, reply_id, has_attachments in rows:
            # 1. Валидируем только те поля, которые есть в БД
            # (exclude_unset=True помогает избежать проблем, если какие-то поля None)
            item = DocumentListItem.model_validate(doc, from_attributes=True)

            # 2. Вручную заполняем поля, которых нет в модели БД
            item.is_read = is_read or False
            item.is_archived = is_archived or False
            item.is_pinned = is_pinned or False
            item.reply_id = reply_id
            item.has_attachments = has_attachments or False
            item.type_name = doc.type.name if doc.type else "Без типа"

            # 3. Заполняем вложенные списки
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
        """Фамилия И.О."""
        if not emp: return "Неизвестно"
        patronymic = f"{emp.patronymic[0]}." if emp.patronymic else ""
        return f"{emp.last_name} {emp.first_name[0]}.{patronymic}"