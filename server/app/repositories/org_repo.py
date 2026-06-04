from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from server.app.database.employee_models import Department, EmployeePosition, Employee


class OrgRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_departments_by_org(self, org_id: int) -> list[Department]:
        """Получить все подразделения организации"""
        result = await self.db.execute(
            select(Department).where(Department.organization_id == org_id)
        )
        return list(result.scalars().all())

    async def get_employees_by_dept(self, dept_id: int) -> list[EmployeePosition]:
        """Получить всех сотрудников в отделе через таблицу позиций"""
        stmt = (
            select(EmployeePosition)
            .join(Employee)
            .where(EmployeePosition.department_id == dept_id)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())