from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.database.employee_models import Overtime, EmployeePosition


class OvertimeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add(self, data):
        new_record = Overtime(**data.model_dump())
        self.db.add(new_record)
        await self.db.commit()
        await self.db.refresh(new_record)
        return new_record

    async def get_by_id(self, ot_id: int):
        result = await self.db.execute(select(Overtime).where(Overtime.id == ot_id))
        return result.scalar_one_or_none()

    async def update_note(self, ot_id: int, note: str):
        stmt = (
            update(Overtime)
            .where(Overtime.id == ot_id)
            .values(note_text=note)
            .returning(Overtime)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none()

    async def update_all(self, ot_id: int, update_dict: dict):
        stmt = update(Overtime).where(Overtime.id == ot_id).values(**update_dict).returning(Overtime)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none()

    async def get_by_employee_id(self, employee_id: int):
        result = await self.db.execute(
            select(Overtime).where(Overtime.employee_id == employee_id).order_by(Overtime.overtime_date.desc())
        )
        return result.scalars().all()

    async def get_by_dept_id(self, dept_id: int):
        stmt = (
            select(Overtime)
            .join(EmployeePosition, Overtime.employee_id == EmployeePosition.employee_id)
            .where(EmployeePosition.department_id == dept_id)
            .order_by(Overtime.overtime_date.desc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_all(self):
        result = await self.db.execute(select(Overtime).order_by(Overtime.overtime_date.desc()))
        return result.scalars().all()

    async def delete(self, ot_id: int):
        result = await self.db.execute(
            delete(Overtime).where(Overtime.id == ot_id).returning(Overtime.id)
        )
        await self.db.commit()
        return result.scalar_one_or_none()