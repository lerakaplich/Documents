from datetime import date
from typing import Optional

from sqlalchemy import select, update, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from server.app.database.employee_models import Department, EmployeePosition, Employee, Organization
from server.app.schemas.org import DepartmentCreate, OrganizationCreate
from server.app.schemas.org.structure_search import AncestorItem, StructureEntityType


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
        """Получить подразделение с предзагрузкой руководителя и типа подразделения."""
        stmt = (
            select(Department)
            .options(
                joinedload(Department.head),
                joinedload(Department.department_type)
            )
            .where(Department.id == dept_id)
        )
        result = await self.db.execute(stmt)
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

    async def get_departments_with_hierarchy_by_ids(self, dept_ids: set[int]) -> dict[int, list[AncestorItem]]:
        """
        Принимает set(dept_ids), находит их hierarchy_path,
        вытаскивает все родительские Департаменты и Организацию,
        возвращая словарь: {dept_id: [Ancestor(Org), Ancestor(ParentDept), Ancestor(Dept)]}
        """
        if not dept_ids:
            return {}

        # 1. Загружаем целевые департаменты
        res = await self.db.execute(
            select(Department).where(Department.id.in_(dept_ids))
        )
        target_depts = list(res.scalars().all())

        # 2. Собираем все ID отделов и организаций из hierarchy_path (например "1/4/12")
        all_needed_dept_ids = set()
        all_needed_org_ids = set()

        dept_paths_map: dict[int, list[int]] = {}

        for dept in target_depts:
            # В зависимости от того, как у вас хранится path (строкой "1/4/12" или списками):
            if dept.hierarchy_path:
                # Разбиваем path по слэшу
                ids = [int(x) for x in dept.hierarchy_path.split("/") if x.isdigit()]
                dept_paths_map[dept.id] = ids
                all_needed_dept_ids.update(ids)
            else:
                dept_paths_map[dept.id] = [dept.id]
                all_needed_dept_ids.add(dept.id)

            if dept.organization_id:
                all_needed_org_ids.add(dept.organization_id)

        # 3. Загружаем все участвующие Отделы и Организации за 2 запроса
        depts_res = await self.db.execute(
            select(Department).where(Department.id.in_(all_needed_dept_ids))
        )
        depts_dict = {d.id: d for d in depts_res.scalars().all()}

        orgs_res = await self.db.execute(
            select(Organization).where(Organization.id.in_(all_needed_org_ids))
        )
        orgs_dict = {o.id: o for o in orgs_res.scalars().all()}

        # 4. Собираем для каждого целевого dept_id полный список предков
        hierarchy_result: dict[int, list[AncestorItem]] = {}

        for dept in target_depts:
            ancestors: list[AncestorItem] = []

            # а) Сначала добавляем Организацию
            if dept.organization_id and dept.organization_id in orgs_dict:
                org = orgs_dict[dept.organization_id]
                ancestors.append(
                    AncestorItem(
                        id=org.id,
                        name=org.name,
                        type=StructureEntityType.ORGANIZATION,
                    )
                )

            # б) Затем добавляем цепочку отделов по порядку из hierarchy_path
            path_ids = dept_paths_map.get(dept.id, [dept.id])
            for d_id in path_ids:
                if d_id in depts_dict:
                    d = depts_dict[d_id]
                    ancestors.append(
                        AncestorItem(
                            id=d.id,
                            name=d.name,
                            type=StructureEntityType.DEPARTMENT,
                        )
                    )

            hierarchy_result[dept.id] = ancestors

        return hierarchy_result