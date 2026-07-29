from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from server.app.database.document_models import (
    DocumentType as DocType,
    Tag,
    Document,
    EmployeeDocument,
    DocumentAttachment,
    DocumentTag,
    DocumentRole
)
from server.app.database.document_models import SystemEmployee  # Предположим, модель сотрудника
from server.app.database.employee_models import Employee, EmployeePosition, Department


class BotRepository:
    def __init__(self, doc_session: AsyncSession, emp_session: AsyncSession = None):
        self.doc_session = doc_session
        self.emp_session = emp_session

    async def get_all_types(self) -> List[DocType]:
        """Возвращает все доступные типы документов"""
        stmt = select(DocType).order_by(DocType.name)
        result = await self.doc_session.execute(stmt)
        return list(result.scalars().all())

    async def get_type_by_id(self, type_id: int) -> Optional[DocType]:
        """Получает тип документа по ID"""
        return await self.doc_session.get(DocType, type_id)

    async def get_tags_paginated(self, page: int = 1, per_page: int = 6) -> tuple[list, int]:
        """
        Возвращает список тегов для текущей страницы и общее количество тегов.
        """
        # Считаем общее количество
        count_stmt = select(func.count(Tag.id))
        total_result = await self.doc_session.execute(count_stmt)
        total_count = total_result.scalar_one_or_none() or 0

        # Получаем теги с пагинацией
        offset = (page - 1) * per_page
        stmt = (
            select(Tag)
            .order_by(Tag.name)
            .offset(offset)
            .limit(per_page)
        )
        result = await self.doc_session.execute(stmt)
        tags = list(result.scalars().all())

        return tags, total_count

    async def get_departments_by_parent(self, parent_id: Optional[int] = None) -> List[Department]:
        """Получает дочерние отделы (если parent_id=None — верхний уровень)"""
        stmt = select(Department).where(Department.parent_id == parent_id).order_by(Department.name)
        res = await self.emp_session.execute(stmt)
        return list(res.scalars().all())

    async def get_employees_by_department(self, department_id: int) -> List[Employee]:
        """Получает всех сотрудников конкретного отдела"""
        stmt = (
            select(Employee)
            .join(Employee.positions)
            .where(EmployeePosition.department_id == department_id)
            .order_by(Employee.last_name)
        )
        res = await self.emp_session.execute(stmt)
        return list(res.scalars().all())

    async def get_all_employees_in_department_tree(self, department_id: int) -> List[int]:
        """Рекурсивно получает ID всех сотрудников отдела и всех его подотделов"""
        # Собираем ID текущего отдела и всех его дочерних структур
        dept_ids = [department_id]

        async def _collect_subdepts(d_id: int):
            sub_depts = await self.get_departments_by_parent(d_id)
            for sd in sub_depts:
                dept_ids.append(sd.id)
                await _collect_subdepts(sd.id)

        await _collect_subdepts(department_id)

        stmt = (
            select(Employee.id)
            .join(Employee.positions)
            .where(EmployeePosition.department_id.in_(dept_ids))
        )
        res = await self.emp_session.execute(stmt)
        return list(res.scalars().all())

    async def save_document_from_fsm(self, data: dict, sender_employee_id: int) -> Document:
        """
        Финальное сохранение документа из данных FSMContext
        """
        # 1. Создаем сам документ
        new_doc = Document(
            type_id=data["type_id"],
            direction=data["direction"],
            title=data.get("title"),
            about=data.get("about"),
            reg_number=data.get("reg_number"),
            deadline=data.get("deadline"),
            source_employee_id=sender_employee_id,
            status="under_review"
        )
        self.doc_session.add(new_doc)
        await self.doc_session.flush()  # Получаем new_doc.id

        # 2. Добавляем автора (sender)
        self.doc_session.add(EmployeeDocument(
            document_id=new_doc.id,
            employee_id=sender_employee_id,
            role=DocumentRole.sender
        ))

        # 3. Добавляем получателей
        for emp_id in data.get("recipients", []):
            self.doc_session.add(EmployeeDocument(
                document_id=new_doc.id,
                employee_id=emp_id,
                role=DocumentRole.recipient
            ))

        # 4. Добавляем исполнителей
        for emp_id in data.get("executors", []):
            self.doc_session.add(EmployeeDocument(
                document_id=new_doc.id,
                employee_id=emp_id,
                role=DocumentRole.executor
            ))

        # 5. Привязываем теги
        for tag_id in data.get("tag_ids", []):
            self.doc_session.add(DocumentTag(
                document_id=new_doc.id,
                tag_id=tag_id
            ))

        # 6. Вложения
        for att in data.get("attachments", []):
            self.doc_session.add(DocumentAttachment(
                document_id=new_doc.id,
                file_name=att["file_name"],
                storage_path=att["storage_path"],
                file_size=att.get("file_size")
            ))

        await self.doc_session.commit()
        return new_doc

    async def get_employee_by_chat_id(self, chat_id: int) -> Optional[Employee]:
        """
        Ищет сотрудника по chat_id (Telegram ID).
        Жадно подгружает должности (positions) и подразделения (department),
        чтобы сразу знать department_id и должность автора.
        """
        if not self.emp_session:
            raise ValueError("emp_session не передан в BotRepository")

        stmt = (
            select(Employee)
            .options(
                joinedload(Employee.positions).joinedload(EmployeePosition.department)
            )
            .where(Employee.chat_id == chat_id)
        )
        result = await self.emp_session.execute(stmt)
        return result.scalars().first()

    async def get_employee_by_id(self, employee_id: int) -> Optional[Employee]:
        """Получает запись сотрудника из базы кадров по его ID"""
        if not self.emp_session:
            raise ValueError("emp_session не передан в BotRepository")

        stmt = (
            select(Employee)
            .options(
                joinedload(Employee.positions).joinedload(EmployeePosition.department)
            )
            .where(Employee.id == employee_id)
        )
        result = await self.emp_session.execute(stmt)
        return result.scalars().first()

    async def get_employees_by_ids(self, employee_ids: list[int]) -> List[Employee]:
        """
        Возвращает список сотрудников по списку их ID (для получения имен участников).
        Запрос адресован в emp_session.
        """
        if not employee_ids:
            return []

        if not self.emp_session:
            raise ValueError("emp_session не передан в BotRepository")

        stmt = (
            select(Employee)
            .where(Employee.id.in_(employee_ids))
            .order_by(Employee.last_name)
        )
        result = await self.emp_session.execute(stmt)
        return list(result.scalars().all())

    async def get_tags_by_ids(self, tag_ids: list[int]) -> List[Tag]:
        """
        Возвращает список тегов по их ID (для отображения наименований тегов).
        Запрос адресован в doc_session.
        """
        if not tag_ids:
            return []

        stmt = (
            select(Tag)
            .where(Tag.id.in_(tag_ids))
            .order_by(Tag.name)
        )
        result = await self.doc_session.execute(stmt)
        return list(result.scalars().all())