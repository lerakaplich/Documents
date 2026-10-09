from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.repositories.dep_type_repo import DepartmentTypeRepository
from server.app.schemas.org import DepartmentTypeCreate, DepartmentTypeUpdate


class DepartmentTypeService:
    def __init__(self, db: AsyncSession):
        self.repo = DepartmentTypeRepository(db)

    async def get_department_type(self, dept_type_id: int):
        dept_type = await self.repo.get_by_id(dept_type_id)
        if not dept_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тип отдела не найден"
            )
        return dept_type

    async def list_department_types(self, skip: int = 0, limit: int = 100):
        return await self.repo.get_all(skip=skip, limit=limit)

    async def create_department_type(self, schema: DepartmentTypeCreate):
        return await self.repo.create(name=schema.name)

    async def update_department_type(self, dept_type_id: int, schema: DepartmentTypeUpdate):
        dept_type = await self.get_department_type(dept_type_id)

        # Обновляем только переданные поля
        new_name = schema.name if schema.name is not None else dept_type.name
        return await self.repo.update(db_obj=dept_type, name=new_name)

    async def delete_department_type(self, dept_type_id: int):
        dept_type = await self.get_department_type(dept_type_id)
        await self.repo.delete(dept_type)
        return {"status": "success", "message": "Тип отдела удален"}