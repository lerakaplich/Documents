# server/app/repositories/employees_repo.py
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from sqlalchemy.orm import selectinload

from server.app.database.employee_models import Employee, EmployeePosition, Department
from server.app.schemas.user_schemas.employee_dto import EmployeePositionCreate, EmployeeCreate


class EmployeesRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, emp_id: int):
        stmt = (
            select(Employee)
            .options(selectinload(Employee.positions))  # ЗАГРУЖАЕМ СРАЗУ!
            .where(Employee.id == emp_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_department(self, department_id: int, include_inactive: bool = False) -> List[Employee]:
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

    async def get_leader_paths(self, employee_id: int) -> List[str]:
        stmt = select(Department.hierarchy_path).join(EmployeePosition).where(
            EmployeePosition.employee_id == employee_id,
            EmployeePosition.is_leader == True
        )
        result = await self.db.execute(stmt)
        # Приводим к list[str], убирая возможные None
        return [path for path in result.scalars().all() if path]

    async def get_target_dept_paths(self, target_emp_id: int) -> List[str]:
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

    async def add_position(self, emp_id: int, pos: EmployeePositionCreate):
        new_pos = EmployeePosition(
            employee_id=emp_id,
            department_id=pos.department_id,
            position_name=pos.position_name,
            # SQLAlchemy автоматически возьмет значение из Enum.value
            assignment_kind=pos.assignment_kind.value,
            is_leader=pos.is_leader
        )
        self.db.add(new_pos)

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

    async def update_employee_position(self, employee_id: int, position_data: EmployeePositionCreate):
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