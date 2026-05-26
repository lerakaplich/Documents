from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, or_, and_, cast, String, desc, asc, exists
from fastapi import HTTPException, status
from typing import List, Optional
from datetime import date

from server.app.config import MSG_TEMPLATE_NEW_REVISION
from server.app.database.models import Document, EmployeeDocument, DocumentType, DocumentRole, AppRights, DocStatus, \
    Employee, Department, Division, Organization, DocDirection, TagPriority, SystemEmployee, Tag, DocumentTag
from datetime import datetime, timezone

from server.app.schemas.doc_schemas.document_dto import DocumentCreateForm, AdminMetadataUpdate
from server.app.services.documents.comment_service import CommentService


class DocumentService:
    def __init__(self, db: AsyncSession, comment_service: CommentService):
        self.db = db
        self.comment_service = comment_service  # Внедряем CRUD-сервис комментов

    async def create(self, payload: DocumentCreateForm, user_id: int) -> Document:
        """Создание документа с автоматической привязкой участников и тегов"""
        type_check = await self.db.execute(select(DocumentType).where(DocumentType.id == payload.type_id))
        if not type_check.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Указанный тип документа не существует.")

        new_doc = Document(
            type_id=payload.type_id,
            direction=payload.direction,
            title=payload.title,
            about=payload.about,
            reg_number=payload.reg_number,
            deadline=payload.deadline,
            file_path=f"storage/docs/{payload.reg_number or 'temp'}.zip"
        )
        self.db.add(new_doc)
        await self.db.flush()

        # Привязываем создателя (sender) и исполнителей -> им согласовывать не нужно (True)
        self.db.add(EmployeeDocument(
            document_id=new_doc.id, employee_id=user_id, role=DocumentRole.sender, is_approved=True
        ))

        for emp_id in payload.executors:
            self.db.add(EmployeeDocument(
                document_id=new_doc.id, employee_id=emp_id, role=DocumentRole.executor, is_approved=True
            ))

        # ИСПРАВЛЕНО: Получатели инициализируются как None (ожидают решения в PyQt6)
        for emp_id in payload.recipients:
            self.db.add(EmployeeDocument(
                document_id=new_doc.id, employee_id=emp_id, role=DocumentRole.recipient, is_approved=None
            ))

        if payload.tag_ids:
            for tag_id in payload.tag_ids:
                self.db.add(DocumentTag(document_id=new_doc.id, tag_id=tag_id))

        await self.db.commit()
        await self.db.refresh(new_doc)
        return new_doc

    async def get_all(
            self,
            user_id: int,
            user_rights: AppRights,
            scope: str = "my",
            is_completed: Optional[bool] = None,
            status_filters: Optional[DocStatus] = None,
            type_id: Optional[int] = None,
            direction: Optional[DocDirection] = None,
            tag_ids: Optional[List[int]] = None,
            date_from: Optional[date] = None,
            date_to: Optional[date] = None,
            search: Optional[str] = None,
            sort_by: str = "created_at",
            sort_order: str = "desc",
    ) -> List[Document]:
        """Главная точка входа для получения реестра документов"""

        # Инициализируем базовый запрос
        query = select(Document).distinct()

        # 1. Применяем слой безопасности и scope
        query = await self._apply_security_and_scope(query, user_id, user_rights, scope)

        # 2. Применяем персональный фильтр выполнения (В работе / Архив)
        query = self._apply_completion_filter(query, scope, is_completed)

        # 3. Применяем кастомные бизнес-фильтры (Тип, Статус, Направление, Даты, Теги)
        query = await self._apply_business_filters(
            query, status_filters, type_id, direction, tag_ids, date_from, date_to
        )

        # 4. Применяем полнотекстовый поиск
        query = self._apply_search(query, search)

        # 5. Применяем сортировку
        query = self._apply_sorting(query, sort_by, sort_order)

        # Выполняем агрегированный запрос
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_id(self, doc_id: int, user_id: int, user_rights: AppRights) -> Document:
        """Получение карточки с автоматической фиксацией прочтения (reads)"""
        result = await self.db.execute(select(Document).where(Document.id == doc_id))
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Документ не найден.")

        # Проверка прав доступа
        if user_rights not in [AppRights.admin, AppRights.superadmin]:
            access_check = await self.db.execute(
                select(EmployeeDocument)
                .where(EmployeeDocument.document_id == doc_id, EmployeeDocument.employee_id == user_id)
            )
            if not access_check.scalar_one_or_none():
                raise HTTPException(status_code=403, detail="Доступ запрещен.")

        # АВТО-ОТМЕТКА О ПРОЧТЕНИИ (public.reads)
        from server.app.database.models import Read
        read_check = await self.db.execute(
            select(Read).where(Read.document_id == doc_id, Read.employee_id == user_id)
        )
        if not read_check.scalar_one_or_none():
            self.db.add(Read(document_id=doc_id, employee_id=user_id))
            await self.db.commit()

        return document

    async def delete(self, doc_id: int) -> None:
        """Удаление документа"""
        result = await self.db.execute(select(Document).where(Document.id == doc_id))
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(status_code=404, detail="Документ не найден.")

        await self.db.execute(delete(Document).where(Document.id == doc_id))
        await self.db.commit()

    async def toggle_complete(self, doc_id: int, user_id: int, is_completed: bool) -> None:
        """
        Переключение персонального статуса выполнения документа (Архивация).
        Меняет флаг is_completed в таблице employee_document строго для текущего пользователя.
        """
        # Ищем связь текущего пользователя с этим документом
        result = await self.db.execute(
            select(EmployeeDocument)
            .where(
                EmployeeDocument.document_id == doc_id,
                EmployeeDocument.employee_id == user_id
            )
        )
        relation = result.scalar_one_or_none()

        # Если записи нет — пользователь не имеет отношения к документу и не может его "выполнить"
        if not relation:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Вы не являетесь участником этого документа, действие заблокировано."
            )

        # Обновляем поля
        relation.is_completed = is_completed
        relation.completed_at = datetime.now(timezone.utc) if is_completed else None

        # Фиксируем изменения в базе
        await self.db.commit()

    # ============================================================================
    # ВНУТРЕННИЕ МЕТОДЫ-СТРОИТЕЛИ (BUILDERS)
    # ============================================================================

    async def _apply_security_and_scope(self, query, user_id: int, user_rights: AppRights, scope: str):
        """Шаг 1: Разграничение прав доступа на основе оргструктуры и scope"""
        if scope == "all" and user_rights in [AppRights.admin, AppRights.superadmin]:
            return query  # Админу в режиме "all" доступно абсолютно всё без джоинов

        # В любых других случаях нам обязательно нужен JOIN с таблицей участников
        query = query.join(EmployeeDocument, Document.id == EmployeeDocument.document_id)
        user_direct_access = (EmployeeDocument.employee_id == user_id)

        if scope == "all":
            # Ищем, какими структурами руководит пользователь
            managed_depts = (
                await self.db.execute(select(Department.id).where(Department.boss_id == user_id))).scalars().all()
            managed_divs = (
                await self.db.execute(select(Division.id).where(Division.boss_id == user_id))).scalars().all()
            managed_orgs = (
                await self.db.execute(select(Organization.id).where(Organization.boss_id == user_id))).scalars().all()

            if any([managed_depts, managed_divs, managed_orgs]):
                # Собираем ID всех подчиненных
                sub_conditions = []
                if managed_depts: sub_conditions.append(Employee.department_id.in_(managed_depts))
                if managed_divs: sub_conditions.append(Employee.division_id.in_(managed_divs))
                if managed_orgs: sub_conditions.append(Employee.organization_id.in_(managed_orgs))

                subordinate_ids = (
                    await self.db.execute(select(Employee.id).where(or_(*sub_conditions)))).scalars().all()

                # Руководитель видит свои доки + доки подчиненных
                return query.where(or_(user_direct_access, EmployeeDocument.employee_id.in_(subordinate_ids)))

        # Если не руководитель или scope="my" — жестко режем по user_id
        return query.where(user_direct_access)

    def _apply_completion_filter(self, query, scope: str, is_completed: Optional[bool]):
        """Шаг 2: Фильтрация по состоянию выполнения (В работе / Архив)"""
        if is_completed is not None and scope != "all":
            query = query.where(EmployeeDocument.is_completed == is_completed)
        return query

    async def _apply_business_filters(
            self, query,
            statuses: Optional[List[DocStatus]],
            type_id: Optional[int],
            direction: Optional[DocDirection],
            tag_ids: Optional[List[int]],
            date_from: Optional[date],
            date_to: Optional[date]
    ):
        """Шаг 3: Наложение бизнес-фильтров с умной логикой приоритетов тегов (И / ИЛИ)"""
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

        if tag_ids:
            # Вычитываем из базы информацию о переданных тегах, чтобы узнать их приоритеты
            tag_data = (await self.db.execute(
                select(Tag.id, Tag.priority).where(Tag.id.in_(tag_ids))
            )).all()

            # Группируем ID по их бизнес-логике
            critical_ids = [t.id for t in tag_data if t.priority in [TagPriority.urgent, TagPriority.important]]
            normal_ids = [t.id for t in tag_data if t.priority == TagPriority.normal]

            # Джоиним таблицу связей Many-to-Many
            query = query.join(DocumentTag, Document.id == DocumentTag.c.document_id)

            conditions = []

            # Если есть обычные теги — они работают через ИЛИ (OR) внутри своей группы
            if normal_ids:
                conditions.append(DocumentTag.c.tag_id.in_(normal_ids))

            # Если есть критические теги — каждый из них должен жестко присутствовать (AND)
            # Поэтому мы добавляем их как отдельные строгие условия
            if critical_ids:
                for crit_id in critical_ids:
                    conditions.append(DocumentTag.c.tag_id == crit_id)

            # Объединяем всё через and_ к основному запросу
            if conditions:
                query = query.where(and_(*conditions))

        return query

    def _apply_search(self, query, search: Optional[str]):
        """
        Шаг 4: Единый сквозной поиск по метаданным документа,
        тегам и ФИО участников через ORM-модели.
        """
        if not search:
            return query

        search_words = search.strip().split()
        if not search_words:
            return query

        word_conditions = []

        for word in search_words:
            pattern = f"%{word}%"

            # 1. Подзапрос для поиска по тегам (используем класс Tag и таблицу связей)
            tag_subquery = (
                select(DocumentTag.c.document_id)
                .join(Tag, Tag.id == DocumentTag.c.tag_id)
                .where(Tag.name.ilike(pattern))
            ).scalar_subquery()

            # 2. Подзапрос для поиска по ФИО (используем классы EmployeeDocument и SystemEmployee)
            employee_subquery = (
                select(EmployeeDocument.document_id)
                .join(SystemEmployee, SystemEmployee.id == EmployeeDocument.employee_id)
                .where(
                    or_(
                        SystemEmployee.last_name.ilike(pattern),
                        SystemEmployee.first_name.ilike(pattern),
                        SystemEmployee.patronymic.ilike(pattern)
                    )
                )
            ).scalar_subquery()

            # Объединяем все условия для текущего слова
            word_conditions.append(
                or_(
                    Document.title.ilike(pattern),
                    Document.about.ilike(pattern),
                    Document.reg_number.ilike(pattern),

                    cast(Document.sequence_number, String).ilike(pattern),
                    cast(Document.sent_date, String).ilike(pattern),
                    cast(Document.deadline, String).ilike(pattern),

                    Document.id.in_(tag_subquery),
                    Document.id.in_(employee_subquery)
                )
            )

        # Документ должен соответствовать каждому введенному слову
        query = query.where(and_(*word_conditions))

        return query

    def _apply_sorting(self, query, sort_by: str, sort_order: str = "desc"):
        """
        Шаг 5: Прогрессивная сортировка на стороне сервера.
        1. Гарантированно выводит документы с тегом 'urgent' на самый верх.
        2. Динамически сортирует по выбранному полю в указанном направлении (asc/desc).
        """
        # --- СЛОЙ 1: АБСОЛЮТНЫЙ ПРИОРИТЕТ СРОЧНЫХ ДОКУМЕНТОВ ---
        # Создаем подзапрос, который проверяет наличие у документа тега со статусом 'urgent'
        urgent_exists = (
            select(1)
            .where(
                and_(
                    DocumentTag.document_id == Document.id,
                    DocumentTag.tag_id == Tag.id,
                    Tag.priority == TagPriority.urgent
                )
            )
            .exists()
        )

        # Первичная сортировка: сначала те, у кого urgent_exists == True (в Postgres True идет после False, поэтому desc)
        query = query.order_by(desc(urgent_exists))

        # --- СЛОЙ 2: ПОЛЬЗОВАТЕЛЬСКАЯ СОРТИРОВКА ПО ПОЛЯМ ---
        # Определяем карту доступных полей для сортировки
        sorting_fields = {
            "title": Document.title,
            "about": Document.about,
            "reg_number": Document.reg_number,
            "sequence_number": Document.sequence_number,
            "sent_date": Document.sent_date,
            "deadline": Document.deadline,
            "created_at": Document.created_at
        }

        # Берем выбранное поле или откатываемся на дату создания
        target_field = sorting_fields.get(sort_by, Document.created_at)

        # Применяем направление сортировки
        if sort_order.lower() == "asc":
            query = query.order_by(asc(target_field))
        else:
            query = query.order_by(desc(target_field))

        return query

    async def admin_update_metadata(self, document_id: int, payload: AdminMetadataUpdate) -> Document:
        """
        Административное обновление любых метаданных документа.
        Исключает проверку бизнес-логики состояний. Полное доверие администратору.
        """
        # 1. Ищем документ в базе данных
        query = select(Document).where(Document.id == document_id)
        result = await self.db.execute(query)
        document = result.scalar_one_or_none()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Документ с ID {document_id} не найден в системе."
            )

        # 2. Превращаем Pydantic-модель в словарь, исключая неуказанные поля (None)
        # update_data = payload.dict(exclude_unset=True) # для старых версий pydantic
        update_data = payload.model_dump(exclude_unset=True)

        if not update_data:
            # Если админ нажал "Сохранить", ничего не поменяв, просто отдаем документ обратно
            return document

        # 3. Динамически обновляем измененные поля объекта модели
        for key, value in update_data.items():
            setattr(document, key, value)

        try:
            # 4. Фиксируем изменения в базе данных
            await self.db.commit()
            # Обновляем состояние объекта, чтобы подгрузить измененные данные (включая связи, если нужно)
            await self.db.refresh(document)
            return document

        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ошибка при сохранении изменений администратора: {str(e)}"
            )

    # ГЛАВНЫЙ МЕТОД СОГЛАСОВАНИЯ
    async def process_review(self, document_id: int, user_id: int, approved: bool):
        """
        Фиксация решения согласующего (True - Утверждено, False - Отклонено).
        """
        # 1. Валидация участника и защита от повторного клика
        emp_doc_record = await self._validate_reviewer(document_id, user_id)

        # 2. Проставляем статус (True или False)
        emp_doc_record.is_approved = approved

        # 3. Скоростной пересчет общего статуса карточки
        await self._recalculate_document_status(document_id)

        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ошибка при сохранении решения участника: {str(e)}"
            )

    async def _recalculate_document_status(self, document_id: int):
        """
        Скоростной пересчет общего статуса документа по трехзначной логике (True / False / Null)
        """
        # 1. Проверяем, отклонил ли документ хотя бы ОДИН человек
        has_rejected_query = select(exists().where(
            and_(EmployeeDocument.document_id == document_id, EmployeeDocument.is_approved == False)
        ))
        has_rejected = (await self.db.execute(has_rejected_query)).scalar()

        # Загружаем документ для изменения статуса
        doc_query = select(Document).where(Document.id == document_id)
        document = (await self.db.execute(doc_query)).scalar_one_or_none()
        if not document:
            return

        # Если есть хоть один отказ (False) -> весь документ падает в статус 'rejected'
        if has_rejected:
            document.status = DocStatus.rejected
            return

        # 2. Проверяем, остался ли хоть кто-то, кто ЕЩЕ НЕ ПРИНЯЛ решение (сидит в NULL/None)
        has_null_query = select(exists().where(
            and_(EmployeeDocument.document_id == document_id, EmployeeDocument.is_approved == None)
        ))
        has_null = (await self.db.execute(has_null_query)).scalar()

        if not has_null:
            # Никто не отклонил и никого в None не осталось -> Значит, абсолютно ВСЕ сказали True
            document.status = DocStatus.approved
        else:
            # Кто-то еще думает (есть None), но проверим, одобрил ли уже ХОТЬ ОДИН согласующий
            has_approved_reviewer_query = select(exists().where(
                and_(
                    EmployeeDocument.document_id == document_id,
                    EmployeeDocument.is_approved == True,
                    EmployeeDocument.role.in_([DocumentRole.recipient, DocumentRole.delegate])
                )
            ))
            has_approved_reviewer = (await self.db.execute(has_approved_reviewer_query)).scalar()

            if has_approved_reviewer:
                document.status = DocStatus.partially_approved
            else:
                document.status = DocStatus.under_review

    async def _validate_reviewer(self, document_id: int, user_id: int) -> EmployeeDocument:
        """Проверка прав участника на выполнение операции review"""
        query = select(EmployeeDocument).where(
            and_(
                EmployeeDocument.document_id == document_id,
                EmployeeDocument.employee_id == user_id
            )
        )
        result = await self.db.execute(query)
        emp_doc = result.scalar_one_or_none()

        if not emp_doc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Вы не являетесь участником данного документа."
            )

        if emp_doc.role not in [DocumentRole.recipient, DocumentRole.delegate]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ваша роль в документе не требует согласования."
            )

        # ИСПРАВЛЕНО: Защита от повторного клика. Если статус уже НЕ None, значит решение принято.
        if emp_doc.is_approved is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Вы уже зафиксировали свое решение (утвердили или отклонили) по этому документу."
            )

        return emp_doc

    # ВНЕСЕНИЕ ПРАВОК
    async def make_revisions(self, document_id: int, user_id: int, text: str) -> None:
        """
        Бизнес-логика фиксации замечаний по документу от согласующей стороны.
        """
        # 1. Проверяем, что голосует именно получатель/делегат
        role_query = select(EmployeeDocument).where(
            and_(
                EmployeeDocument.document_id == document_id,
                EmployeeDocument.employee_id == user_id
            )
        )
        user_relation = (await self.db.execute(role_query)).scalar_one_or_none()

        if not user_relation:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Вы не являетесь участником этого документа."
            )

        if user_relation.role not in [DocumentRole.recipient, DocumentRole.delegate]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Оставлять правки/замечания могут только согласующие лица (получатели или делегаты)."
            )

        # 2. Проверяем существование документа (чтобы выдать красивую 404, если что)
        doc_query = select(Document).where(Document.id == document_id)
        document = (await self.db.execute(doc_query)).scalar_one_or_none()
        if not document:
            raise HTTPException(status_code=404, detail="Документ не найден")

        # 3. Передаем чистый текст в CRUD комментариев
        await self.comment_service.create_comment(
            document_id=document_id,
            user_id=user_id,
            text=text
        )

        # 4. Фиксируем транзакцию
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ошибка сохранения замечания: {str(e)}"
            )

        # 5. Отправляем пуш боту о том, что появились новые замечания
        await self.comment_service.send_notification_stub(document)


