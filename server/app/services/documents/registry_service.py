import asyncio

from cachetools import TTLCache
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.database.document_models import AppRights, DocumentRole
from server.app.database.employee_models import Organization, Department
from server.app.repositories.document_repo import DocumentRepository
from server.app.schemas.doc.doc_employee_dto import ParticipantItem
from server.app.schemas.doc.document_dto import DocumentListItem
from server.app.schemas.doc.tag_dto import TagRead


def _format_fio(emp) -> str:
    """Форматирование ФИО вида: Фамилия И.О."""
    if not emp:
        return "Неизвестно"
    patronymic = f"{emp.patronymic[0]}." if emp.patronymic else ""
    return f"{emp.last_name} {emp.first_name[0]}.{patronymic}"


# Кэши в памяти: максимум 1024 элемента, TTL 5 минут (300 секунд)
_dept_cache = TTLCache(maxsize=1024, ttl=300)
_org_cache = TTLCache(maxsize=1024, ttl=300)


class RegistryService:
    def __init__(self, repo: DocumentRepository, structure_session: AsyncSession):
        self.repo = repo
        self.structure_session = structure_session

    async def fetch_departments_map(self, dept_ids: set[int]) -> dict[int, str]:
        """Возвращает {dept_id: dept_name} из TTLCache или 1 batch-запросом из БД employees."""
        if not dept_ids:
            return {}

        result: dict[int, str] = {}
        missing_ids: set[int] = set()

        # 1. Забираем из кэша
        for d_id in dept_ids:
            if d_id in _dept_cache:
                result[d_id] = _dept_cache[d_id]
            else:
                missing_ids.add(d_id)

        # 2. Недостающие вытягиваем 1 запросом из БД structure_session
        if missing_ids:
            stmt = select(Department.id, Department.name).where(Department.id.in_(missing_ids))
            db_res = await self.structure_session.execute(stmt)

            for d_id, name in db_res.all():
                _dept_cache[d_id] = name
                result[d_id] = name

            # Для ID, которых нет в БД (fallback), тоже кэшируем, чтобы не дёргать БД повторно
            for d_id in missing_ids:
                if d_id not in result:
                    fallback_name = f"Подразделение ID: {d_id}"
                    _dept_cache[d_id] = fallback_name
                    result[d_id] = fallback_name

        return result

    async def fetch_organizations_map(self, org_ids: set[int]) -> dict[int, str]:
        """Возвращает {org_id: org_name} из TTLCache или 1 batch-запросом из БД employees."""
        if not org_ids:
            return {}

        result: dict[int, str] = {}
        missing_ids: set[int] = set()

        for o_id in org_ids:
            if o_id in _org_cache:
                result[o_id] = _org_cache[o_id]
            else:
                missing_ids.add(o_id)

        if missing_ids:
            stmt = select(Organization.id, Organization.name).where(Organization.id.in_(missing_ids))
            db_res = await self.structure_session.execute(stmt)

            for o_id, name in db_res.all():
                _org_cache[o_id] = name
                result[o_id] = name

            for o_id in missing_ids:
                if o_id not in result:
                    fallback_name = f"Организация ID: {o_id}"
                    _org_cache[o_id] = fallback_name
                    result[o_id] = fallback_name

        return result

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

        # 1. Базовый запрос
        query = self.repo.prepare_document_list_query()
        query = self.repo.apply_read_status(query, user_id)
        query = self.repo.apply_archive_status(query, user_id)
        query = self.repo.apply_pin_status(query, user_id)
        query = self.repo.apply_reply_status(query)
        query = self.repo.apply_attachments_status(query)

        # 2. Scope & Rights
        is_admin = user_rights in [AppRights.admin, AppRights.superadmin]
        if scope == "my" or not is_admin:
            query = self.repo.apply_user_scope(query, user_id, is_completed)

        # 3. Фильтры
        query = self.repo.apply_filters(query, filter_params)

        # 4. Поиск
        if search and search.strip():
            for word in search.strip().split():
                query = self.repo.apply_search(query, f"%{word}%")

        # 5. Total
        total = await self.repo.count_query(query)

        # 6. Сортировка и пагинация
        query = self.repo.apply_sorting(query, sort_by, sort_order)
        query = query.limit(limit).offset(offset)

        # 7. Выполнение запроса
        rows = await self.repo.execute_query(query)
        if not rows:
            return 0, []

        # =========================================================================
        # СБОР УНИКАЛЬНЫХ ID ОТДЕЛОВ И ОРГАНИЗАЦИЙ ДЛЯ ТЕКУЩЕЙ СТРАНИЦЫ
        # =========================================================================
        dept_ids: set[int] = set()
        org_ids: set[int] = set()

        for doc, *rest in rows:
            if doc.source_department_id:
                dept_ids.add(doc.source_department_id)
            if doc.source_organization_id:
                org_ids.add(doc.source_organization_id)

            receivers = getattr(doc, "receivers", []) or []
            for rec in receivers:
                if rec.target_department_id:
                    dept_ids.add(rec.target_department_id)
                if rec.target_organization_id:
                    org_ids.add(rec.target_organization_id)

        # Запрашиваем маппинги параллельно из 2-й базы (БД employees) с учётом TTLCache
        departments_map, organizations_map = await asyncio.gather(
            self.fetch_departments_map(dept_ids),
            self.fetch_organizations_map(org_ids)
        )

        # =========================================================================
        # 8. МАППИНГ DTO
        # =========================================================================
        items = []
        for doc, is_read, is_archived, is_pinned, reply_id, has_attachments in rows:
            item = DocumentListItem.model_validate(doc, from_attributes=True)

            item.is_read = is_read or False
            item.is_archived = is_archived or False
            item.is_pinned = is_pinned or False
            item.reply_id = reply_id
            item.has_attachments = has_attachments or False
            item.type_name = doc.type.name if doc.type else "Без типа"

            # --- Вычисление отправителя (sender) ---
            source_emp = next(
                (ed.employee for ed in doc.employees if ed.employee_id == doc.source_employee_id),
                None
            )

            if source_emp:
                sender_name = _format_fio(source_emp)
            elif getattr(doc, "source_official_text", None):
                sender_name = doc.source_official_text
            elif doc.source_department_id:
                sender_name = departments_map.get(
                    doc.source_department_id, f"Подразделение ID: {doc.source_department_id}"
                )
            elif doc.source_organization_id:
                sender_name = organizations_map.get(
                    doc.source_organization_id, f"Организация ID: {doc.source_organization_id}"
                )
            else:
                sender_name = "Не указан"

            item.sender = ParticipantItem(name=sender_name, role=DocumentRole.sender)

            # --- Вычисление получателей (recipients) ---
            receivers = getattr(doc, "receivers", None)
            if receivers:
                item.recipients = []
                for rec in receivers:
                    if getattr(rec, "target_official_text", None):
                        rec_name = rec.target_official_text
                    elif rec.target_department_id:
                        rec_name = departments_map.get(
                            rec.target_department_id, f"Подразделение ID: {rec.target_department_id}"
                        )
                    elif rec.target_organization_id:
                        rec_name = organizations_map.get(
                            rec.target_organization_id, f"Организация ID: {rec.target_organization_id}"
                        )
                    else:
                        rec_name = "Получатель без наименования"

                    item.recipients.append(
                        ParticipantItem(name=rec_name, role=DocumentRole.recipient)
                    )
            else:
                item.recipients = [
                    ParticipantItem(name=_format_fio(ed.employee), role=ed.role)
                    for ed in doc.employees
                    if ed.role == DocumentRole.recipient
                ]

            # Список всех связанных участников
            item.participants = [
                ParticipantItem(name=_format_fio(ed.employee), role=ed.role)
                for ed in doc.employees
            ]

            item.tags = [
                TagRead(id=tag.id, name=tag.name, priority=tag.priority, color=tag.color)
                for tag in doc.tags
            ]

            items.append(item)

        return total, items

