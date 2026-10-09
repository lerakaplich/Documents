from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.database.employee_models import DepartmentType


class DepartmentTypeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, dept_type_id: int) -> DepartmentType | None:
        result = await self.db.execute(
            select(DepartmentType).where(DepartmentType.id == dept_type_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[DepartmentType]:
        result = await self.db.execute(
            select(DepartmentType).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, name: str) -> DepartmentType:
        db_obj = DepartmentType(name=name)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(self, db_obj: DepartmentType, name: str) -> DepartmentType:
        db_obj.name = name
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, db_obj: DepartmentType) -> None:
        await self.db.delete(db_obj)
        await self.db.commit()