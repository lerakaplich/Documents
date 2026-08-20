# server/app/repositories/employees_repo.py
from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, distinct, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.expression import delete

from server.app.database.employee_models import Employee, EmployeePosition, Department
from server.app.schemas.org import DepartmentPathItem
from server.app.schemas.user_schemas.employee_dto import PositionCreate, EmployeeCreate, PositionUpdate


class EmployeesRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_active(self) -> list[Employee]:
        """Возвращает список всех работающих сотрудников для кэширования при импорте"""
        stmt = select(Employee).where(Employee.is_active == True)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_short_by_org_id_paginated(
        self,
        org_id: int,
        show_fired: bool = False,
        page: int = 1,
        size: int = 20
    ):
        # Базовые условия фильтрации
        where_conditions = [Department.organization_id == org_id]
        if not show_fired:
            where_conditions.append(Employee.is_active == True)

        # 1. Считаем общее количество уникальных сотрудников в организации
        count_stmt = (
            select(func.count(distinct(Employee.id)))
            .select_from(Employee)
            .join(EmployeePosition, EmployeePosition.employee_id == Employee.id)
            .join(Department, Department.id == EmployeePosition.department_id)
            .where(*where_conditions)
        )
        total = await self.db.scalar(count_stmt) or 0

        # 2. Выбираем только необходимые поля с пагинацией
        offset = (page - 1) * size
        stmt = (
            select(
                Employee.id,
                Employee.last_name,
                Employee.first_name,
                Employee.patronymic
            )
            .distinct()
            .join(EmployeePosition, EmployeePosition.employee_id == Employee.id)
            .join(Department, Department.id == EmployeePosition.department_id)
            .where(*where_conditions)
            .order_by(Employee.last_name, Employee.first_name)
            .offset(offset)
            .limit(size)
        )

        result = await self.db.execute(stmt)
        return result.all(), total

    async def get_by_id(self, emp_id: int):
        stmt = (
            select(Employee)
            .options(selectinload(Employee.positions))  # ЗАГРУЖАЕМ СРАЗУ!
            .where(Employee.id == emp_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_primary_department_id(self, employee_id: int) -> Optional[int]:
        """Получает ID текущего (активного) подразделения сотрудника"""
        today = date.today()
        stmt = (
            select(EmployeePosition.department_id)
            .where(
                EmployeePosition.employee_id == employee_id,
                EmployeePosition.start_date <= today,
                or_(
                    EmployeePosition.end_date >= today,
                    EmployeePosition.end_date.is_(None)
                )
            )
            .order_by(EmployeePosition.start_date.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_departments(self, employee_id: int) -> Optional[Employee]:
        """Загружает сотрудника вместе с должностями, отделами и их типами."""
        stmt = (
            select(Employee)
            .where(Employee.id == employee_id)
            .options(
                selectinload(Employee.positions)
                .selectinload(EmployeePosition.department)
                .selectinload(Department.department_type)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_departments_by_ids(self, dept_ids: set[int]) -> dict[int, Department]:
        """Вытягивает подразделения по их ID за один запрос."""
        if not dept_ids:
            return {}
        stmt = (
            select(Department)
            .where(Department.id.in_(dept_ids))
            .options(selectinload(Department.department_type))
        )
        result = await self.db.execute(stmt)
        return {d.id: d for d in result.scalars().all()}

    async def get_by_department(self, department_id: int, include_inactive: bool = False) -> list[Employee]:
        stmt = (
            select(Employee)
            .join(EmployeePosition)
            .where(EmployeePosition.department_id == department_id)
            .options(selectinload(Employee.positions))
        )

        # Фильтр по активности
        if not include_inactive:
            stmt = stmt.where(Employee.is_active == True)

        stmt = stmt.distinct()
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_paginated_employees(self, limit: int, offset: int, show_fired: bool = False):
        query = select(
            Employee.id,
            func.concat_ws(' ', Employee.last_name, Employee.first_name, Employee.patronymic).label("full_name"),
            EmployeePosition.position_name,
            Department.name.label("department_name"),
            Employee.phone_number
        ).select_from(Employee) \
         .join(EmployeePosition) \
         .join(Department)

        # Фильтр активности
        if not show_fired:
            query = query.where(Employee.is_active == True)

        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        return result.all()

    async def get_leader_paths(self, employee_id: int) -> list[str]:
        stmt = select(Department.hierarchy_path).join(EmployeePosition).where(
            EmployeePosition.employee_id == employee_id,
            EmployeePosition.is_leader == True
        )
        result = await self.db.execute(stmt)
        # Приводим к list[str], убирая возможные None
        return [path for path in result.scalars().all() if path]

    async def get_target_dept_paths(self, target_emp_id: int) -> list[str]:
        stmt = select(Department.hierarchy_path).join(EmployeePosition).where(
            EmployeePosition.employee_id == target_emp_id
        )
        result = await self.db.execute(stmt)
        return [path for path in result.scalars().all() if path]

    async def add_employee(self, data: EmployeeCreate) -> Employee:
        new_emp = Employee(
            service_number=data.service_number,
            last_name=data.last_name,
            first_name=data.first_name,
            patronymic=data.patronymic,
            phone_number=data.phone_number,
            work_number=data.work_number,
            email=data.email,
            birth_date=data.birth_date
        )
        self.db.add(new_emp)
        await self.db.flush()  # Получаем ID до commit
        return new_emp

    async def add_position(self, employee_id: int, dept_id: int, name: str, is_leader: bool) -> EmployeePosition:
        new_pos = EmployeePosition(
            employee_id=employee_id,
            department_id=dept_id,
            position_name=name,
            is_leader=is_leader
        )
        self.db.add(new_pos)
        await self.db.flush()
        await self.db.refresh(new_pos)
        return new_pos

    async def delete_position(self, position_id: int) -> None:
        stmt = delete(EmployeePosition).where(EmployeePosition.id == position_id)
        await self.db.execute(stmt)
        await self.db.flush()

    async def get_dept_path_by_id(self, dept_id: int) -> Optional[str]:
        stmt = select(Department.hierarchy_path).where(Department.id == dept_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_employee_with_positions(self, employee_id: int):
        stmt = (
            select(Employee)
            .options(selectinload(Employee.positions))
            .filter(Employee.id == employee_id)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def update_employee_profile(self, employee_id: int, update_data: dict):
        # Обновляем все переданные поля (включая is_active)
        stmt = (
            update(Employee)
            .where(Employee.id == employee_id)
            .values(**update_data)
            .returning(Employee)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.scalar_one()

    async def update_employee_position(self, employee_id: int, position_data: PositionCreate):
        # Предполагаем, что у сотрудника одна активная позиция или нам нужно обновить конкретную
        stmt = (
            update(EmployeePosition)
            .where(EmployeePosition.employee_id == employee_id)
            .values(
                department_id=position_data.department_id,
                position_name=position_data.position_name,
                assignment_kind=position_data.assignment_kind,
                is_leader=position_data.is_leader
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def update_is_leader(self, position_id: int, is_leader: bool):
        stmt = (
            update(EmployeePosition)
            .where(EmployeePosition.id == position_id)
            .values(is_leader=is_leader)
        )
        await self.db.execute(stmt)
        await self.db.flush()
        return True

    async def get_position_by_id(self, position_id: int) -> Optional[EmployeePosition]:
        result = await self.db.execute(
            select(EmployeePosition).filter(EmployeePosition.id == position_id)
        )
        return result.scalar_one_or_none()

    async def update_department_head(self, dept_id: int, emp_id: int):
        stmt = (
            update(Department)
            .where(Department.id == dept_id)
            .values(head_employee_id=emp_id)
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def get_position_by_employee_and_dept(self, employee_id: int, department_id: int) -> Optional[
        EmployeePosition]:
        stmt = select(EmployeePosition).where(
            EmployeePosition.employee_id == employee_id,
            EmployeePosition.department_id == department_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_positions_by_employee(self, employee_id: int) -> list[EmployeePosition]:
        stmt = select(EmployeePosition).where(EmployeePosition.employee_id == employee_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_position(self, data: PositionUpdate) -> None:
        # Используем update() для изменения полей записи по ID
        stmt = (
            update(EmployeePosition)
            .where(EmployeePosition.id == data.id)
            .values(
                department_id=data.department_id,
                position_name=data.position_name,
                is_leader=data.is_leader
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def get_department_codes_for_employee(self, employee_id: int) -> tuple[str, str]:
        """
        Возвращает (код_высшего_подразделения, код_отдела) для сотрудника.
        """
        # Получаем подразделение сотрудника с подгрузкой Department
        stmt = (
            select(Department)
            .join(EmployeePosition, EmployeePosition.department_id == Department.id)
            .where(EmployeePosition.employee_id == employee_id)
        )
        result = await self.db.execute(stmt)
        dept = result.scalar_one_or_none()

        if not dept:
            return "00", "00"

        sub_dept_code = str(dept.number) if getattr(dept, 'number', None) is not None else dept.name

        # Если у нас есть hierarchy_path (например "1/4/12"), извлекаем корень
        if hasattr(dept, 'hierarchy_path') and dept.hierarchy_path:
            top_dept_id = int(dept.hierarchy_path.split('/')[0])
            top_res = await self.db.execute(select(Department).where(Department.id == top_dept_id))
            top_dept = top_res.scalar_one_or_none()
            top_dept_code = (str(top_dept.number) if top_dept and getattr(top_dept, 'number',
                                                                          None) is not None else top_dept.name) if top_dept else sub_dept_code
        else:
            top_dept_code = sub_dept_code

        return top_dept_code, sub_dept_code

    async def get_chat_ids_by_employee_ids(self, employee_ids: list[int]) -> dict[int, int]:
        """Возвращает словарь {employee_id: chat_id} только для тех, у кого заполнено поле"""
        if not employee_ids:
            return {}

        stmt = (
            select(Employee.id, Employee.chat_id)
            .where(
                Employee.id.in_(employee_ids),
                Employee.chat_id.is_not(None),
                Employee.is_active == True
            )
        )
        result = await self.db.execute(stmt)
        return {row.id: row.chat_id for row in result.all()}

    async def get_all_active_chat_ids(self) -> list[int]:
        """Возвращает список chat_id всех активных сотрудников для массовых анонсов"""
        stmt = (
            select(Employee.chat_id)
            .where(
                Employee.is_active == True,
                Employee.chat_id.is_not(None)
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_employees_by_org_id(self, org_id: int) -> list[Employee]:
        """
        Возвращает уникальных сотрудников организации с жадной загрузкой их должностей.
        """
        stmt = (
            select(Employee)
            .options(
                # Жадно подгружаем positions, чтобы Pydantic смог их прочитать без Lazy Load
                selectinload(Employee.positions)
            )
            .distinct()
            .join(EmployeePosition, EmployeePosition.employee_id == Employee.id)
            .join(Department, Department.id == EmployeePosition.department_id)
            .where(
                Department.organization_id == org_id,
                Employee.is_active.is_(True)
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())