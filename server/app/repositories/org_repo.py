from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from server.app.database.employee_models import Department, EmployeePosition, Employee
from server.app.schemas.user_schemas.org_dto import DepartmentCreate


class OrgRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_departments_by_org(self, org_id: int) -> list[Department]:
        result = await self.db.execute(
            select(Department)
            .options(joinedload(Department.department_type)) # Подгружаем тип!
            .where(Department.organization_id == org_id)
        )
        return list(result.scalars().all())

    async def get_department_by_id(self, dept_id: int) -> Optional[Department]:
        result = await self.db.execute(
            select(Department)
            .options(joinedload(Department.department_type)) # И здесь тоже
            .where(Department.id == dept_id)
        )
        return result.scalar_one_or_none()
    async def get_employees_by_dept(self, dept_id: int) -> list[EmployeePosition]:
        """Получить всех сотрудников в отделе через таблицу позиций"""
        stmt = (
            select(EmployeePosition)
            .join(Employee)
            .where(EmployeePosition.department_id == dept_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_department(self, data: DepartmentCreate) -> Department:
        new_dept = Department(
            organization_id=data.organization_id,
            parent_id=data.parent_id,
            department_type_id=data.department_type_id,  # Передаем тип
            name=data.name,
            number=data.number,
            phone_number=data.phone_number
        )
        self.db.add(new_dept)
        await self.db.flush()
        await self.db.refresh(new_dept, attribute_names=['department_type'])
        return new_dept

    async def update_path(self, dept_id: int, path: str):
        dept = await self.get_department_by_id(dept_id)
        if dept:
            dept.hierarchy_path = path
            await self.db.commit()  # Или flush, в зависимости от вашей транзакционной модели