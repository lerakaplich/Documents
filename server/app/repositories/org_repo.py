from datetime import date
from typing import Optional

from sqlalchemy import select, update, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from server.app.database.employee_models import Department, EmployeePosition, Employee, Organization
from server.app.schemas.org import DepartmentCreate, OrganizationCreate


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
            await self.db.flush()  # Или flush, в зависимости от вашей транзакционной модели

    async def update_organization(self, org_id: int, data: dict) -> None:
        stmt = (
            update(Organization)
            .where(Organization.id == org_id)
            .values(**data)
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def get_dept_path_by_id(self, dept_id: int) -> Optional[str]:
        """Быстрое получение пути департамента для проверки прав."""
        result = await self.db.execute(
            select(Department.hierarchy_path).where(Department.id == dept_id)
        )
        return result.scalar_one_or_none()

    async def get_organization_by_id(self, org_id: int) -> Optional[Organization]:
        """Получить организацию по ID."""
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        return result.scalar_one_or_none()

    async def update_department(self, dept_id: int, data: dict) -> Department:
        stmt = (
            update(Department)
            .where(Department.id == dept_id)
            .values(**data)
        )
        await self.db.execute(stmt)
        await self.db.flush()

        return await self.get_department_by_id(dept_id)

    async def update_department_head(self, dept_id: int, employee_id: Optional[int]):
        """Обновляет ID руководителя подразделения."""
        stmt = (
            update(Department)
            .where(Department.id == dept_id)
            .values(head_employee_id=employee_id)
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def has_children(self, dept_id: int) -> bool:
        """Проверяет, есть ли у департамента дочерние подразделения."""
        result = await self.db.execute(
            select(Department).where(Department.parent_id == dept_id).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def delete_department(self, dept_id: int):
        """Удаляет подразделение."""
        from sqlalchemy import delete
        stmt = delete(Department).where(Department.id == dept_id)
        await self.db.execute(stmt)
        await self.db.flush()

    async def update_parent(self, dept_id: int, new_parent_id: Optional[int]):
        """Обновляет родителя департамента."""
        await self.db.execute(
            update(Department)
            .where(Department.id == dept_id)
            .values(parent_id=new_parent_id)
        )
        await self.db.flush()

    async def get_all_descendants(self, dept_id: int) -> list[Department]:
        """Получает всех потомков (рекурсивно или по пути) для пересчета."""
        # Для простоты используем поиск по path (это самый быстрый способ)
        # Если путь '1/2/3', то все потомки начинаются с '1/2/3/'
        path = await self.get_dept_path_by_id(dept_id)
        result = await self.db.execute(
            select(Department).where(Department.hierarchy_path.like(f"{path}%"))
        )
        return list(result.scalars().all())

    async def get_department_detail(self, dept_id: int) -> Optional[Department]:
        result = await self.db.execute(
            select(Department)
            .options(
                joinedload(Department.department_type),
                joinedload(Department.head_employee)
            )
            .where(Department.id == dept_id)
        )
        return result.scalar_one_or_none()

    async def create_organization(self, data: OrganizationCreate) -> Organization:
        new_org = Organization(
            unp=data.unp,
            smdo_code=data.smdo_code,
            name=data.name,
            short_name=data.short_name,  # <-- Передаем в модель
            phone_number=data.phone_number,
            address=data.address,
            email=data.email,
            is_subscriber=data.is_subscriber
        )
        self.db.add(new_org)
        await self.db.flush()
        await self.db.refresh(new_org)
        return new_org

    async def get_all_organizations(self, limit: int = 100, offset: int = 0) -> list[Organization]:
        stmt = select(Organization).offset(offset).limit(limit).order_by(Organization.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_organization_by_unp(self, unp: str) -> Optional[Organization]:
        result = await self.db.execute(
            select(Organization).where(Organization.unp == unp)
        )
        return result.scalar_one_or_none()

    async def delete_organization(self, org_id: int) -> None:
        stmt = delete(Organization).where(Organization.id == org_id)
        await self.db.execute(stmt)
        await self.db.flush()

    async def has_linked_entities(self, org_id: int) -> bool:
        """Проверка, привязаны ли к организации подразделения (для безопасного удаления)"""
        result = await self.db.execute(
            select(Department.id).where(Department.organization_id == org_id).limit(1)
        )
        return result.scalar_one_or_none() is not None