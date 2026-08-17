from datetime import date, time

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.database.employee_models import Overtime, EmployeePosition, Department


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

    async def get_by_ids(self, ot_ids: list[int]):
        if not ot_ids:
            return []
        result = await self.db.execute(select(Overtime).where(Overtime.id.in_(ot_ids)))
        return result.scalars().all()

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
        # 1. Получаем hierarchy_path целевого отдела
        target_dept_path = await self.db.scalar(
            select(Department.hierarchy_path).where(Department.id == dept_id)
        )

        # Если отдел не найден или путь не заполнен, делаем фолбэк на точное совпадение
        if not target_dept_path:
            stmt = (
                select(Overtime)
                .join(
                    EmployeePosition,
                    Overtime.employee_id == EmployeePosition.employee_id,
                )
                .where(EmployeePosition.department_id == dept_id)
                .order_by(Overtime.overtime_date.desc())
                .distinct()
            )
            result = await self.db.execute(stmt)
            return result.scalars().all()

        # 2. Выбираем переработки всех сотрудников из целевого и всех вложенных отделов
        # Сравнение по префиксу: hierarchy_path LIKE '1/4%'
        stmt = (
            select(Overtime)
            .join(
                EmployeePosition,
                Overtime.employee_id == EmployeePosition.employee_id,
            )
            .join(Department, EmployeePosition.department_id == Department.id)
            .where(Department.hierarchy_path.like(f"{target_dept_path}%"))
            .order_by(Overtime.overtime_date.desc())
            .distinct()
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

    async def check_exists(self, employee_id: int, overtime_date: date, start_time: time, end_time: time) -> bool:
        """Проверяет, существует ли уже переработка у сотрудника на эту дату и время"""
        stmt = (
            select(Overtime)
            .where(
                Overtime.employee_id == employee_id,
                Overtime.overtime_date == overtime_date,
                Overtime.overtime_start == start_time,
                Overtime.overtime_end == end_time
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def create_overtime_direct(self, employee_id: int, overtime_date: date, start_time: time, end_time: time,
                                     description: str):
        """Прямая запись переработки (используется при автоимпорте)"""
        new_record = Overtime(
            employee_id=employee_id,
            overtime_date=overtime_date,
            overtime_start=start_time,
            overtime_end=end_time,
            note_text=description
        )
        self.db.add(new_record)
        # commit() здесь делать НЕ НАДО, сервис импорта сделает один общий commit в конце файла
        return new_record

    async def update_bulk_notes_for_employee(self, overtime_ids: list[int], employee_id: int, note: str):
        stmt = (
            update(Overtime)
            .where(
                Overtime.id.in_(overtime_ids),
                Overtime.employee_id == employee_id
            )
            .values(note_text=note)
        )
        await self.db.execute(stmt)
        await self.db.commit()
        return {"updated_count": len(overtime_ids)}