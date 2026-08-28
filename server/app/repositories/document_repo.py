from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc, exists, insert, delete, update, case
from sqlalchemy.dialects.postgresql import insert as pg_insert
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy.orm import selectinload, joinedload

# ИСПРАВЛЕНО: Импортируем сущности строго из новой схемы db_documents
from server.app.database.document_models import (
    Document, EmployeeDocument, SystemEmployee,
    Tag, DocumentTag, DocStatus, DocDirection, AppRights, TagPriority, DocumentRole, RedirectHistory, Read,
    DocumentArchive, DocumentPin, DocumentAttachment, DocumentStatusHistory, DocumentType, DocumentReceiver
)
from server.app.database.employee_models import Department, EmployeePosition
from server.app.schemas.user_schemas.doc_participants import DocumentParticipantsDTO


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

    async def assign_role_to_employee(self, doc_id: int, emp_id: int, role: DocumentRole):
        """Безопасное добавление участника"""
        stmt = pg_insert(EmployeeDocument).values(
            document_id=doc_id,
            employee_id=emp_id,
            role=role
        ).on_conflict_do_nothing(
            # ВАЖНО: Имя должно строго совпадать с тем, что сейчас в БД!
            constraint="unique_doc_employee"
        ).returning(EmployeeDocument.id)

        result = await self.db.execute(stmt)
        return result.scalar() is not None

    async def assign_role_to_employees_bulk(self, doc_id: int, emp_ids: list[int], role: DocumentRole) -> list[int]:
        """
        Массовое безопасное добавление участников.
        Возвращает список employee_id, которые были успешно добавлены (не были дубликатами).
        """
        if not emp_ids:
            return []

        values = [
            {"document_id": doc_id, "employee_id": emp_id, "role": role}
            for emp_id in emp_ids
        ]

        stmt = pg_insert(EmployeeDocument).values(values).on_conflict_do_nothing(
            constraint="unique_doc_employee"
        ).returning(EmployeeDocument.employee_id)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def remove_employee_from_doc(self, doc_id: int, emp_id: int):
        """Удаление сотрудника из документа"""
        stmt = delete(EmployeeDocument).where(
            EmployeeDocument.document_id == doc_id,
            EmployeeDocument.employee_id == emp_id
        )
        await self.db.execute(stmt)

    async def add_redirect_history(self, doc_id: int, from_id: int, to_id: int, message: str):
        """Запись в лог перенаправлений"""
        stmt = insert(RedirectHistory).values(
            document_id=doc_id,
            from_employee_id=from_id,
            to_employee_id=to_id,
            message=message
        )
        await self.db.execute(stmt)

    async def add_redirect_history_bulk(self, doc_id: int, from_id: int, to_ids: list[int], message: Optional[str]):
        """Массовая запись в лог перенаправлений"""
        if not to_ids:
            return

        values = [
            {
                "document_id": doc_id,
                "from_employee_id": from_id,
                "to_employee_id": to_id,
                "message": message
            }
            for to_id in to_ids
        ]
        stmt = insert(RedirectHistory).values(values)
        await self.db.execute(stmt)

    async def get_participants(self, doc_id: int) -> list[EmployeeDocument]:
        """Получить список всех текущих участников документа"""
        result = await self.db.execute(
            select(EmployeeDocument).where(EmployeeDocument.document_id == doc_id)
        )
        return list(result.scalars().all())

    async def get_redirect_history(self, doc_id: int) -> list[RedirectHistory]:
        """Получить историю перенаправлений"""
        result = await self.db.execute(
            select(RedirectHistory)
            .where(RedirectHistory.document_id == doc_id)
            .order_by(RedirectHistory.redirected_at.desc())
        )
        return list(result.scalars().all())

    async def get_rights_map(self, emp_ids: list[int]) -> dict:
        """
        Быстрый запрос для получения прав по списку ID сотрудников.
        Возвращает словарь {emp_id: rights_value}
        """
        if not emp_ids:
            return {}

        stmt = select(SystemEmployee.id, SystemEmployee.rights).where(SystemEmployee.id.in_(emp_ids))
        result = await self.db.execute(stmt)

        # Превращаем результат в удобный словарь
        return {row.id: row.rights for row in result.all()}

    async def get_system_employee(self, emp_id: int) -> Optional[SystemEmployee]:
        """Получить запись о сотруднике из БД документов для сверки"""
        result = await self.db.execute(select(SystemEmployee).where(SystemEmployee.id == emp_id))
        return result.scalar_one_or_none()

    async def upsert_system_employee(
            self,
            id: int,
            last_name: str,
            first_name: str,
            patronymic: Optional[str],
            rights: AppRights
    ):
        """
        Единственный метод для синхронизации данных сотрудника в СЭД.
        Гарантирует отсутствие NULL в обязательных полях.
        """
        stmt = pg_insert(SystemEmployee).values(
            id=id,
            last_name=last_name,
            first_name=first_name,
            patronymic=patronymic,
            rights=rights
        ).on_conflict_do_update(
            index_elements=['id'],
            set_={
                'last_name': last_name,
                'first_name': first_name,
                'patronymic': patronymic,
                'rights': rights
            }
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def get_system_employee_by_id(self, employee_id: int) -> Optional[SystemEmployee]:
        """Получить запись о сотруднике по ID (для проверки прав)"""
        result = await self.db.execute(select(SystemEmployee).where(SystemEmployee.id == employee_id))
        return result.scalar_one_or_none()

    async def update_last_comment(self, document_id: int, text: str):
        """Обновляет денормализованный текст последнего комментария."""
        stmt = (
            update(Document)
            .where(Document.id == document_id)
            .values(last_comment_text=text.strip())
        )
        await self.db.execute(stmt)

    async def add_read_entry(self, doc_id: int, user_id: int):
        """Добавляет запись в таблицу reads с защитой от дублей."""
        stmt = pg_insert(Read).values(
            document_id=doc_id,
            employee_id=user_id,
            read_at=datetime.now(timezone.utc)
        )
        # Если запись уже есть (CONSTRAINT unique_user_document_read), ничего не делаем
        stmt = stmt.on_conflict_do_nothing(
            index_elements=['employee_id', 'document_id']
        )
        await self.db.execute(stmt)

    async def get_unread_counts_by_group(self, user_id: int):
        """
        Возвращает список кортежей: (type_id, direction, count)
        """
        # Считаем только те, где юзер есть в участниках, но нет в таблице reads
        unread_subquery = (
            select(EmployeeDocument.document_id)
            .where(EmployeeDocument.employee_id == user_id)
            .except_(
                select(Read.document_id)
                .where(Read.employee_id == user_id)
            )
        ).scalar_subquery()

        query = (
            select(
                Document.type_id,
                Document.direction,
                func.count(Document.id).label("count")
            )
            .join(EmployeeDocument, Document.id == EmployeeDocument.document_id)
            .where(Document.id.in_(unread_subquery))
            .group_by(Document.type_id, Document.direction)
        )

        result = await self.db.execute(query)
        return result.all()

    def prepare_document_list_query(self):
        return (
            select(Document)
            .options(
                selectinload(Document.type),
                selectinload(Document.tags),
                selectinload(Document.employees).joinedload(EmployeeDocument.employee),
                selectinload(Document.receivers)  # Подгружается, т.к. DocumentReceiver живет в этой же БД
            )
        )

    def apply_user_scope(self, query, user_id: int, is_completed: Optional[bool]):
        """Ограничивает выборку документами пользователя."""
        stmt = select(1).where(
            and_(
                EmployeeDocument.document_id == Document.id,
                EmployeeDocument.employee_id == user_id
            )
        )
        if is_completed is not None:
            stmt = stmt.where(EmployeeDocument.is_completed == is_completed)
        return query.where(stmt.exists())

    def apply_archive_filter(self, query, user_id: int, is_archived: bool | None):
        """
        Фильтрация документов по персональному архиву пользователя:
        - is_archived = True:  показать ТОЛЬКО архивированные пользователем документы.
        - is_archived = False: показать ТОЛЬКО НЕархивированные документы.
        - is_archived = None:  не фильтровать (показывать и те, и другие).
        """
        if is_archived is None:
            return query

        archive_exists = select(1).where(
            and_(
                DocumentArchive.document_id == Document.id,
                DocumentArchive.employee_id == user_id
            )
        ).exists()

        if is_archived:
            return query.where(archive_exists)
        else:
            return query.where(~archive_exists)

    def apply_filters(self, query, params: dict, user_id: int):
        """Универсальное применение фильтров из словаря параметров."""
        # Фильтр по архиву
        is_archived = params.get('is_archived')
        if is_archived is not None:
            archive_exists = select(1).where(
                and_(
                    DocumentArchive.document_id == Document.id,
                    DocumentArchive.employee_id == user_id
                )
            ).exists()
            query = query.where(archive_exists if is_archived else ~archive_exists)

        # Остальные базовые фильтры
        if params.get('status_filters'):
            query = query.where(Document.status.in_(params['status_filters']))
        if params.get('type_id'):
            query = query.where(Document.type_id == params['type_id'])
        if params.get('direction'):
            query = query.where(Document.direction == params['direction'])
        if params.get('date_from'):
            query = query.where(Document.sent_date >= params['date_from'])
        if params.get('date_to'):
            query = query.where(Document.sent_date <= params['date_to'])

        return query

    def apply_search(self, query, pattern: str):
        """Добавляет условие полнотекстового поиска."""
        return query.where(or_(
            Document.title.ilike(pattern),
            Document.about.ilike(pattern),
            Document.reg_number.ilike(pattern),
            Document.id.in_(select(DocumentTag.document_id).join(Tag).where(Tag.name.ilike(pattern)).scalar_subquery()),
            Document.id.in_(select(EmployeeDocument.document_id).join(SystemEmployee).where(
                or_(SystemEmployee.last_name.ilike(pattern), SystemEmployee.first_name.ilike(pattern))
            ).scalar_subquery())
        ))

    def apply_sorting(self, query, sort_by: str, sort_order: str, user_id: int):
        """
        Сортировка реестра документов:
        Срочные документы всегда идут первыми (если приоритет не переопределен),
        затем применяется указанное поле сортировки.
        """
        # 1. По умолчанию срочные документы поднимаются вверх
        urgent_exists = exists().where(
            and_(
                DocumentTag.document_id == Document.id,
                DocumentTag.tag_id == Tag.id,
                Tag.priority == TagPriority.urgent
            )
        )
        query = query.order_by(desc(urgent_exists))

        # 2. Вычисляемые выражения для сложных полей

        # Сортировка по приоритету тегов (urgent=3, important=2, normal=1, без тегов=0)
        max_tag_priority = (
            select(
                case(
                    (Tag.priority == TagPriority.urgent, 3),
                    (Tag.priority == TagPriority.important, 2),
                    (Tag.priority == TagPriority.normal, 1),
                    else_=0
                )
            )
            .select_from(DocumentTag)
            .join(Tag, DocumentTag.tag_id == Tag.id)
            .where(DocumentTag.document_id == Document.id)
            .order_by(
                case(
                    (Tag.priority == TagPriority.urgent, 3),
                    (Tag.priority == TagPriority.important, 2),
                    (Tag.priority == TagPriority.normal, 1),
                    else_=0
                ).desc()
            )
            .limit(1)
            .scalar_subquery()
        )

        # Сортировка по прочитанности (Прочитан = 1, Не прочитан = 0)
        is_read_subquery = exists().where(
            and_(
                Read.document_id == Document.id,
                Read.employee_id == user_id
            )
        )

        # 3. Карта соответствия ключей API полям/выражениям базы данных
        fields = {
            "sequence_number": Document.sequence_number,  # порядковый номер
            "title": Document.title,  # тема
            "about": Document.about,  # касается
            "sent_date": Document.sent_date,  # дата отправки
            "deadline": Document.deadline,  # дедлайн
            "reg_number": Document.reg_number,  # номер документа
            "status": Document.status,  # статус
            "tag_priority": max_tag_priority,  # приоритет тэгов
            "is_read": is_read_subquery,  # прочитанность
            "created_at": Document.created_at,  # дата создания (по умолчанию)
        }

        # Получаем целевое поле для сортировки
        target = fields.get(sort_by, Document.created_at)

        # Применяем направление (asc/desc)
        order_func = asc if sort_order.lower() == "asc" else desc

        # Для NULL значений (например, если нет дедлайна или номера) задаем предсказуемый порядок
        return query.order_by(order_func(target).nulls_last())

    async def count_query(self, query):
        """Подсчет общего количества записей (без учета limit/offset)."""
        count_q = select(func.count()).select_from(query.subquery())
        return (await self.db.execute(count_q)).scalar() or 0

    def apply_read_status(self, query, user_id: int):
        """
        Присоединяет информацию о прочтении.
        Если запись в таблице reads найдена, is_read будет TRUE, иначе NULL (превращаем в False).
        """
        # Создаем алиас для таблицы reads для конкретного пользователя
        read_alias = select(Read.document_id).where(Read.employee_id == user_id).scalar_subquery()

        # Добавляем вычисляемое поле в запрос
        return query.add_columns(
            (Document.id.in_(read_alias)).label("is_read")
        )

    def apply_attachments_status(self, query):
        """
        Присоединяет информацию о наличии вложений.
        has_attachments будет True, если в таблице Attachment есть записи для данного документа.
        """
        attachments_exist = select(DocumentAttachment.document_id).where(
            DocumentAttachment.document_id == Document.id
        ).exists()

        return query.add_columns(attachments_exist.label("has_attachments"))

    async def execute_query(self, query):
        """Выполнение запроса, который возвращает пары (Document, is_read)."""
        result = await self.db.execute(query)
        # unique() нужен, если в запросе есть JOIN по коллекции (tags/employees)
        return result.unique().all()

    async def archive_document(self, doc_id: int, user_id: int):
        stmt = pg_insert(DocumentArchive).values(
            document_id=doc_id,
            employee_id=user_id
        ).on_conflict_do_nothing()

        await self.db.execute(stmt)
        await self.db.commit()

    async def unarchive_document(self, doc_id: int, user_id: int):
        stmt = delete(DocumentArchive).where(
            DocumentArchive.document_id == doc_id,
            DocumentArchive.employee_id == user_id
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def check_user_has_role(self, doc_id: int, user_id: int) -> bool:
        """Проверяет, привязан ли пользователь к документу (есть ли у него любая роль)."""
        stmt = select(func.count()).select_from(EmployeeDocument).where(
            EmployeeDocument.document_id == doc_id,
            EmployeeDocument.employee_id == user_id
        )
        result = await self.db.execute(stmt)
        count = result.scalar()
        return (count or 0) > 0

    def apply_archive_status(self, query, user_id: int):
        archive_exists = select(DocumentArchive.document_id).where(
            DocumentArchive.document_id == Document.id,
            DocumentArchive.employee_id == user_id
        ).exists()

        return query.add_columns(archive_exists.label("is_archived"))

    async def pin_document(self, doc_id: int, user_id: int):
        stmt = pg_insert(DocumentPin).values(document_id=doc_id, employee_id=user_id).on_conflict_do_nothing()
        await self.db.execute(stmt)
        await self.db.commit()

    async def unpin_document(self, doc_id: int, user_id: int):
        stmt = delete(DocumentPin).where(DocumentPin.document_id == doc_id, DocumentPin.employee_id == user_id)
        await self.db.execute(stmt)
        await self.db.commit()

    def apply_pin_status(self, query, user_id: int):
        # Убедитесь, что вы возвращаете результат применения add_columns!
        pin_exists = select(DocumentPin.document_id).where(
            DocumentPin.document_id == Document.id,
            DocumentPin.employee_id == user_id
        ).exists()

        return query.add_columns(pin_exists.label("is_pinned"))

    def apply_reply_status(self, query):
        """
        Выбирает ID первого попавшегося ответа на документ.
        """
        # 1. Создаем подзапрос для выборки ID документа-ответа
        # Нам нужно найти дочерний документ, где parent_document_id равен ID текущего документа
        reply_subquery = select(Document.id).where(
            Document.parent_document_id == Document.id  # Коррелированный подзапрос
        ).limit(1).scalar_subquery()  # Вот здесь .scalar_subquery() нужен, так как это SELECT

        # 2. Добавляем колонку к основному запросу
        return query.add_columns(reply_subquery.label("reply_id"))

    async def add_status_history(self, history_entry: DocumentStatusHistory) -> None:
        """Сохранение записи об изменении статуса документа в базу данных"""
        self.db.add(history_entry)

    async def get_current_timestamp(self):
        """Вспомогательный метод для получения текущего времени сервера бэкенда"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc)

    async def get_status_history_by_doc_id(self, document_id: int) -> list[DocumentStatusHistory]:
        """Получение хронологической истории изменения статусов документа"""
        query = (
            select(DocumentStatusHistory)
            .where(DocumentStatusHistory.document_id == document_id)
            .order_by(DocumentStatusHistory.changed_at.asc())
            .options(selectinload(DocumentStatusHistory.employee))  # Сразу подгружаем ФИО сотрудника
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_next_sequence_number(self, type_id: int) -> int:
        """Глобально вычисляет следующий порядковый номер для типа документа"""
        query = (
            select(func.max(Document.sequence_number))
            .where(Document.type_id == type_id)
        )

        res = await self.db.execute(query)
        max_num = res.scalar_one_or_none()

        return (max_num + 1) if max_num is not None else 1

    async def is_auto_num_enabled(self, type_id: int) -> bool:
        """Проверяет, включена ли автонумерация для типа документа"""
        query = select(DocumentType.auto_num).where(DocumentType.id == type_id)
        res = await self.db.execute(query)
        return res.scalar_one_or_none() or False

    async def get_employee_department_codes(cadre_db: AsyncSession, employee_id: int) -> tuple[str, str]:
        """
        Возвращает (код_высшего_подразделения, код_отдела) для сотрудника.
        Пример ответа: ("10", "102") или ("УИТ", "ОАСУP")
        """
        # 1. Находим должность и отдел сотрудника
        stmt = (
            select(Department)
            .join(EmployeePosition, EmployeePosition.department_id == Department.id)
            .where(EmployeePosition.employee_id == employee_id)
        )
        res = await cadre_db.execute(stmt)
        current_dept = res.scalar_one_or_none()

        if not current_dept:
            return "00", "00"

        # В качестве кода отдела берем number (если есть) или name
        sub_dept_code = str(current_dept.number) if current_dept.number else current_dept.name

        # 2. Поднимаемся к корневому подразделению (где parent_id IS NULL)
        top_dept = current_dept
        while top_dept.parent_id is not None:
            parent_res = await cadre_db.execute(
                select(Department).where(Department.id == top_dept.parent_id)
            )
            parent_dept = parent_res.scalar_one_or_none()
            if not parent_dept:
                break
            top_dept = parent_dept

        top_dept_code = str(top_dept.number) if top_dept.number else top_dept.name

        return top_dept_code, sub_dept_code

    async def get_document_participants_dto(self, doc_id: int) -> DocumentParticipantsDTO:
        """Группирует участников документа по их ролям"""
        participants = await self.get_participants(doc_id)

        sender_id = None
        executors = []
        recipients = []
        delegates = []

        for p in participants:
            if p.role == DocumentRole.sender:  # или автора, смотрим твой Enum DocumentRole
                sender_id = p.employee_id
            elif p.role == DocumentRole.executor:
                executors.append(p.employee_id)
            elif p.role == DocumentRole.recipient:
                recipients.append(p.employee_id)
            elif p.role == DocumentRole.delegate:
                delegates.append(p.employee_id)

        return DocumentParticipantsDTO(
            sender_id=sender_id,
            executors=executors,
            recipients=recipients,
            delegates=delegates
        )

    async def get_unanswered_documents(self) -> list[Document]:
        """
        Возвращает документы, требующие ответа (needs_response = True),
        на которые еще нет ни одного ответного документа (где parent_document_id == doc.id).
        """
        # Подзапрос: получаем список всех parent_document_id (ID документов, на которые уже ответили)
        answered_parent_ids = (
            select(Document.parent_document_id)
            .where(Document.parent_document_id.is_not(None))
            .scalar_subquery()
        )

        # Основной запрос: documents, где needs_response = True и id NOT IN (answered_parent_ids)
        stmt = (
            select(Document)
            .where(
                Document.needs_response.is_(True),
                Document.id.not_in(answered_parent_ids)
            )
            .options(
                # Загружаем участников вместе с их данными system_employees
                selectinload(Document.employees).selectinload(EmployeeDocument.employee)
            )
            .order_by(Document.created_at.desc())
        )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_detail_by_id(self, doc_id: int, user_id: int):
        """
        Получает документ со всеми атрибутами (вложения, теги, участники)
        и вычисляемыми статусами пользователя (is_read, is_archived, is_pinned, reply_id).
        """
        query = (
            select(Document)
            .where(Document.id == doc_id)
            .options(
                selectinload(Document.employees).joinedload(EmployeeDocument.employee),
                selectinload(Document.tags),
                selectinload(Document.attachments),
                selectinload(Document.type)
            )
        )

        # Применяем вычисляемые поля
        query = self.apply_read_status(query, user_id)
        query = self.apply_archive_status(query, user_id)
        query = self.apply_pin_status(query, user_id)
        query = self.apply_reply_status(query)
        query = self.apply_attachments_status(query)

        result = await self.db.execute(query)
        return result.unique().first()

    async def mark_as_read_bulk(self, doc_ids: list[int], employee_id: int) -> list[int]:
        """
        Массовая безопасная фиксация прочтения документов через PostgreSQL ON CONFLICT DO NOTHING.
        Возвращает список id документов, которые были успешно обработаны.
        """
        if not doc_ids:
            return []

        values = [
            {
                "document_id": d_id,
                "employee_id": employee_id,
                "read_at": datetime.now(timezone.utc)
            }
            for d_id in doc_ids
        ]

        stmt = (
            pg_insert(Read)
            .values(values)
            .on_conflict_do_nothing(index_elements=['employee_id', 'document_id'])
        )

        await self.db.execute(stmt)
        await self.db.commit()
        return doc_ids

    async def ensure_read_mark(self, doc_id: int, employee_id: int) -> None:
        """Фиксирует прочтение документа сотрудником, если отметка еще не стоит"""
        stmt = select(Read).where(Read.document_id == doc_id, Read.employee_id == employee_id)
        result = await self.db.execute(stmt)
        if not result.scalar_one_or_none():
            self.db.add(Read(document_id=doc_id, employee_id=employee_id))
            await self.db.commit()