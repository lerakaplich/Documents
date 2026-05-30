from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, cast, String, desc, asc, exists
from typing import List, Optional, Tuple
from datetime import date

# ИСПРАВЛЕНО: Импортируем сущности строго из новой схемы db_documents
from server.app.database.document_models import (
    Document, EmployeeDocument, SystemEmployee,
    Tag, DocumentTag, DocStatus, DocDirection, AppRights, TagPriority
)


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, doc_id: int) -> Optional[Document]:
        """Получить один документ по ID"""
        result = await self.db.execute(select(Document).where(Document.id == doc_id))
        return result.scalar_one_or_none()

    async def delete(self, doc_id: int) -> None:
        """Удалить документ"""
        document = await self.get_by_id(doc_id)
        if document:
            await self.db.delete(document)

    async def get_user_relation(self, doc_id: int, user_id: int) -> Optional[EmployeeDocument]:
        """Получить запись о роли и статусе согласования пользователя в документе"""
        result = await self.db.execute(
            select(EmployeeDocument).where(
                and_(EmployeeDocument.document_id == doc_id, EmployeeDocument.employee_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    async def has_any_rejections(self, doc_id: int) -> bool:
        """Проверить, отклонен ли документ кем-либо из участников"""
        query = select(exists().where(
            and_(EmployeeDocument.document_id == doc_id, EmployeeDocument.is_approved == False)
        ))
        return (await self.db.execute(query)).scalar() or False

    async def has_any_pending(self, doc_id: int) -> bool:
        """Проверить, есть ли пользователи, ожидающие согласования"""
        query = select(exists().where(
            and_(EmployeeDocument.document_id == doc_id, EmployeeDocument.is_approved == None)
        ))
        return (await self.db.execute(query)).scalar() or False

    async def has_any_approvals(self, doc_id: int, roles: list) -> bool:
        """Проверить наличие согласований по конкретным ролям"""
        query = select(exists().where(
            and_(
                EmployeeDocument.document_id == doc_id,
                EmployeeDocument.is_approved == True,
                EmployeeDocument.role.in_(roles)
            )
        ))
        return (await self.db.execute(query)).scalar() or False

    async def get_paginated_list(
            self,
            user_id: int,
            user_rights: AppRights,
            is_completed: Optional[bool],
            statuses: Optional[List[DocStatus]],
            type_id: Optional[int],
            direction: Optional[DocDirection],
            tag_ids: Optional[List[int]],
            date_from: Optional[date],
            date_to: Optional[date],
            search: Optional[str],
            sort_by: str,
            sort_order: str,
            limit: int,
            offset: int
    ) -> Tuple[int, List[Document]]:
        """
        Выборка документов для главной таблицы PyQt6 с пагинацией.
        Логика прав: Admin/Superadmin видят всё. User — только свои документы.
        """
        # Базовый запрос
        query = select(Document)

        # 1. ОГРАНИЧЕНИЕ ПРАВ И ОБЛАСТИ ВИДИМОСТИ (SCOPE)
        if user_rights not in [AppRights.admin, AppRights.superadmin]:
            # Обычный пользователь (User) жестко ограничен только своими документами через EXISTS
            allowed_emp_stmt = select(1).where(
                and_(
                    EmployeeDocument.document_id == Document.id,
                    EmployeeDocument.employee_id == user_id
                )
            )

            # Фильтр выполнения задачи (В работе / Архив) для пользователя
            if is_completed is not None:
                allowed_emp_stmt = allowed_emp_stmt.where(EmployeeDocument.is_completed == is_completed)

            query = query.where(allowed_emp_stmt.exists())

        else:
            # Для админов фильтр "В работе / Архив" применяется глобально ко всей таблице связей,
            # если нужно отфильтровать документы, где хоть кто-то (или целевой маркер) завершил задачу
            if is_completed is not None:
                admin_archive_stmt = select(1).where(
                    and_(
                        EmployeeDocument.document_id == Document.id,
                        EmployeeDocument.is_completed == is_completed
                    )
                )
                query = query.where(admin_archive_stmt.exists())

        # 2. БИЗНЕС-ФИЛЬТРЫ
        if statuses:
            query = query.where(Document.status.in_(statuses))
        if type_id:
            query = query.where(Document.type_id == type_id)
        if direction:
            query = query.where(Document.direction == direction)
        if date_from:
            query = query.where(Document.sent_date >= date_from)
        if date_to:
            query = query.where(Document.sent_date <= date_to)

        # 3. УМНЫЕ ТЕГИ (С учетом нового Many-to-Many соответствия)
        if tag_ids:
            # Ищем приоритеты выбранных тегов
            tag_data = (await self.db.execute(select(Tag.id, Tag.priority).where(Tag.id.in_(tag_ids)))).all()
            critical_ids = [t.id for t in tag_data if t.priority in [TagPriority.urgent, TagPriority.important]]
            normal_ids = [t.id for t in tag_data if t.priority == TagPriority.normal]

            # Связываем через явный JOIN для пересечения
            query = query.join(DocumentTag, Document.id == DocumentTag.document_id)
            conditions = []
            if normal_ids:
                conditions.append(DocumentTag.tag_id.in_(normal_ids))
            if critical_ids:
                for crit_id in critical_ids:
                    conditions.append(DocumentTag.tag_id == crit_id)
            if conditions:
                query = query.where(and_(*conditions))

        # 4. ПОЛНОТЕКСТОВЫЙ ПОИСК (Поиск по словам)
        if search and search.strip():
            for word in search.strip().split():
                pattern = f"%{word}%"

                # Подзапрос поиска по тегам
                tag_subquery = (
                    select(DocumentTag.document_id)
                    .join(Tag, Tag.id == DocumentTag.tag_id)
                    .where(Tag.name.ilike(pattern))
                    .scalar_subquery()
                )

                # Подзапрос поиска по участникам через локальную таблицу system_employees
                emp_subquery = (
                    select(EmployeeDocument.document_id)
                    .join(SystemEmployee, SystemEmployee.id == EmployeeDocument.employee_id)
                    .where(
                        or_(
                            SystemEmployee.last_name.ilike(pattern),
                            SystemEmployee.first_name.ilike(pattern),
                            SystemEmployee.patronymic.ilike(pattern)
                        )
                    )
                    .scalar_subquery()
                )

                query = query.where(or_(
                    Document.title.ilike(pattern),
                    Document.about.ilike(pattern),
                    Document.reg_number.ilike(pattern),
                    Document.last_comment_text.ilike(pattern),
                    cast(Document.sequence_number, String).ilike(pattern),
                    Document.id.in_(tag_subquery),
                    Document.id.in_(emp_subquery)
                ))

        # 5. ПОДСЧЕТ КОЛИЧЕСТВА ЗАПИСЕЙ (TOTAL) С ПОМОЩЬЮ СУБЗАПРОСА
        count_query = select(func.count()).select_from(query.subquery())
        total_count = (await self.db.execute(count_query)).scalar() or 0

        # 6. СОРТИРОВКА (Сначала всегда Срочные/Важные, затем по выбору пользователя)
        urgent_exists = select(1).where(
            and_(
                DocumentTag.document_id == Document.id,
                DocumentTag.tag_id == Tag.id,
                Tag.priority == TagPriority.urgent
            )
        ).exists()
        query = query.order_by(desc(urgent_exists))

        sorting_fields = {
            "title": Document.title,
            "about": Document.about,
            "reg_number": Document.reg_number,
            "sequence_number": Document.sequence_number,
            "sent_date": Document.sent_date,
            "deadline": Document.deadline,
            "created_at": Document.created_at
        }
        target_field = sorting_fields.get(sort_by, Document.created_at)
        query = query.order_by(asc(target_field) if sort_order.lower() == "asc" else desc(target_field))

        # 7. СРЕЗ ПАГИНАЦИИ
        query = query.limit(limit).offset(offset)

        # 8. ВЫПОЛНЕНИЕ
        result = await self.db.execute(query)
        return total_count, list(result.scalars().all())