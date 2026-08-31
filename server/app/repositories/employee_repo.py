# server/app/repositories/employees_repo.py
from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, distinct, or_
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.sql.expression import delete

from server.app.database.employee_models import Employee, EmployeePosition, Department, Organization
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
        today = date.today()
        # Базовые условия фильтрации
        where_conditions = [
            Department.organization_id == org_id,
            EmployeePosition.start_date <= today,
            or_(
                EmployeePosition.end_date.is_(None),
                EmployeePosition.end_date >= today
            )
        ]
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

    async def get_employees_by_dept(self, dept_id: int) -> list[EmployeePosition]:
        """
        Получить все АКТИВНЫЕ позиции сотрудников в отделе с учетом дат начала и окончания.
        """
        today = date.today()
        stmt = (
            select(EmployeePosition)
            .options(
                joinedload(EmployeePosition.employee)
            )
            .join(Employee, Employee.id == EmployeePosition.employee_id)
            .where(
                EmployeePosition.department_id == dept_id,
                Employee.is_active == True,
                EmployeePosition.start_date <= today,
                or_(
                    EmployeePosition.end_date.is_(None),
                    EmployeePosition.end_date >= today
                )
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_department_head_id(self, dept_id: int) -> Optional[int]:
        """
        Возвращает employee_id руководителя отдела.
        Ищет активную позицию с флагом is_head=True (или по названию должности).
        """
        today = date.today()
        stmt = (
            select(EmployeePosition.employee_id)
            .join(Employee, Employee.id == EmployeePosition.employee_id)
            .where(
                EmployeePosition.department_id == dept_id,
                Employee.is_active.is_(True),
                EmployeePosition.is_leader.is_(True),
                EmployeePosition.start_date <= today,
                or_(
                    EmployeePosition.end_date.is_(None),
                    EmployeePosition.end_date >= today
                )
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, emp_id: int) -> Optional[Employee]:
        today = date.today()
        stmt = (
            select(Employee)
            .options(
                selectinload(Employee.positions.and_(
                    EmployeePosition.start_date <= today,
                    or_(
                        EmployeePosition.end_date.is_(None),
                        EmployeePosition.end_date >= today
                    )
                ))
            )
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
        """Загружает сотрудника вместе с АКТИВНЫМИ должностями, отделами и их типами."""
        today = date.today()
        stmt = (
            select(Employee)
            .where(Employee.id == employee_id)
            .options(
                selectinload(
                    Employee.positions.and_(
                        EmployeePosition.start_date <= today,
                        or_(
                            EmployeePosition.end_date.is_(None),
                            EmployeePosition.end_date >= today
                        )
                    )
                )
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
        """Возвращает сотрудников отдела, учитывая активность должности по датам."""
        today = date.today()
        stmt = (
            select(Employee)
            .join(EmployeePosition)
            .where(
                EmployeePosition.department_id == department_id,
                EmployeePosition.start_date <= today,
                or_(
                    EmployeePosition.end_date.is_(None),
                    EmployeePosition.end_date >= today
                )
            )
            .options(
                selectinload(
                    Employee.positions.and_(
                        EmployeePosition.start_date <= today,
                        or_(
                            EmployeePosition.end_date.is_(None),
                            EmployeePosition.end_date >= today
                        )
                    )
                )
            )
        )

        if not include_inactive:
            stmt = stmt.where(Employee.is_active == True)

        stmt = stmt.distinct()
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_paginated_employees(self, limit: int, offset: int, show_fired: bool = False):
        today = date.today()
        query = select(
            Employee.id,
            func.concat_ws(' ', Employee.last_name, Employee.first_name, Employee.patronymic).label("full_name"),
            EmployeePosition.position_name,
            Department.name.label("department_name"),
            Employee.phone_number
        ).select_from(Employee) \
         .join(EmployeePosition) \
         .join(Department) \
         .where(
            EmployeePosition.start_date <= today,
            or_(
                EmployeePosition.end_date.is_(None),
                EmployeePosition.end_date >= today
            )
        )

        # Фильтр активности
        if not show_fired:
            query = query.where(Employee.is_active == True)

        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        return result.all()

    async def get_leader_paths(self, employee_id: int) -> list[str]:
        today = date.today()
        stmt = select(Department.hierarchy_path).join(EmployeePosition).where(
            EmployeePosition.employee_id == employee_id,
            EmployeePosition.is_leader == True,
            EmployeePosition.start_date <= today,
            or_(
                EmployeePosition.end_date.is_(None),
                EmployeePosition.end_date >= today
            )
        )
        result = await self.db.execute(stmt)
        return [path for path in result.scalars().all() if path]

    async def get_target_dept_paths(self, target_emp_id: int) -> list[str]:
        today = date.today()
        stmt = select(Department.hierarchy_path).join(EmployeePosition).where(
            EmployeePosition.employee_id == target_emp_id,
            EmployeePosition.start_date <= today,
            or_(
                EmployeePosition.end_date.is_(None),
                EmployeePosition.end_date >= today
            )
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

    async def add_position(
        self,
        employee_id: int,
        dept_id: int,
        name: str,
        is_leader: bool,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> EmployeePosition:
        new_pos = EmployeePosition(
            employee_id=employee_id,
            department_id=dept_id,
            position_name=name,
            is_leader=is_leader,
            start_date=start_date or date.today(),
            end_date=end_date
        )
        self.db.add(new_pos)
        await self.db.flush()
        await self.db.refresh(new_pos)
        return new_pos

    async def close_position(self, position_id: int, end_date: Optional[date] = None) -> bool:
        close_date = end_date or date.today()
        stmt = (
            update(EmployeePosition)
            .where(
                EmployeePosition.id == position_id,
                or_(
                    EmployeePosition.end_date.is_(None),
                    EmployeePosition.end_date > close_date
                )
            )
            .values(end_date=close_date)
            .returning(EmployeePosition.id)  # Возвращаем ID обновленной записи
        )

        result = await self.db.execute(stmt)
        updated_id = result.scalar_one_or_none()
        await self.db.flush()

        return updated_id is not None

    async def delete_position(self, position_id: int) -> None:
        stmt = delete(EmployeePosition).where(EmployeePosition.id == position_id)
        await self.db.execute(stmt)
        await self.db.flush()

    async def get_dept_path_by_id(self, dept_id: int) -> Optional[str]:
        stmt = select(Department.hierarchy_path).where(Department.id == dept_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_employee_with_positions(self, employee_id: int) -> Optional[Employee]:
        """Загружает сотрудника и только его ТЕКУЩИЕ (активные) должности."""
        today = date.today()
        stmt = (
            select(Employee)
            .options(
                selectinload(
                    Employee.positions.and_(
                        EmployeePosition.start_date <= today,
                        or_(
                            EmployeePosition.end_date.is_(None),
                            EmployeePosition.end_date >= today
                        )
                    )
                )
            )
            .where(Employee.id == employee_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

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

    async def update_is_leader(self, position_id: int, is_leader: bool) -> bool:
        """Обновляет статус руководителя у конкретной активной должности."""
        today = date.today()
        stmt = (
            update(EmployeePosition)
            .where(
                EmployeePosition.id == position_id,
                EmployeePosition.start_date <= today,
                or_(
                    EmployeePosition.end_date.is_(None),
                    EmployeePosition.end_date >= today
                )
            )
            .values(is_leader=is_leader)
            .returning(EmployeePosition.id)
        )
        result = await self.db.execute(stmt)
        updated_id = result.scalar_one_or_none()
        await self.db.flush()
        return updated_id is not None

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
        today = date.today()
        stmt = select(EmployeePosition).where(
            EmployeePosition.employee_id == employee_id,
            EmployeePosition.department_id == department_id,
            EmployeePosition.start_date <= today,
            or_(
                EmployeePosition.end_date.is_(None),
                EmployeePosition.end_date >= today
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_positions_by_employee(
            self,
            employee_id: int,
            only_active: bool = True
    ) -> list[EmployeePosition]:
        """
        Возвращает список должностей сотрудника.
        По умолчанию (only_active=True) возвращает только текущие активные должности.
        """
        stmt = select(EmployeePosition).where(EmployeePosition.employee_id == employee_id)

        if only_active:
            today = date.today()
            stmt = stmt.where(
                EmployeePosition.start_date <= today,
                or_(
                    EmployeePosition.end_date.is_(None),
                    EmployeePosition.end_date >= today
                )
            )

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_position(self, data: PositionUpdate) -> None:
        update_values = {}
        if data.department_id is not None:
            update_values["department_id"] = data.department_id
        if data.position_name is not None:
            update_values["position_name"] = data.position_name
        if data.is_leader is not None:
            update_values["is_leader"] = data.is_leader
        if data.start_date is not None:
            update_values["start_date"] = data.start_date
        if data.end_date is not None:
            update_values["end_date"] = data.end_date

        if update_values:
            stmt = (
                update(EmployeePosition)
                .where(EmployeePosition.id == data.id)
                .values(**update_values)
            )
            await self.db.execute(stmt)
            await self.db.flush()

    async def update_employee_position(self, employee_id: int, position_data: PositionCreate) -> None:
        """Обновляет текущую позицию сотрудника с учетом дат."""
        update_values = {
            "department_id": position_data.department_id,
            "position_name": position_data.position_name,
            "is_leader": position_data.is_leader,
            "start_date": position_data.start_date,
            "end_date": position_data.end_date,
        }
        today = date.today()
        stmt = (
            update(EmployeePosition)
            .where(
                EmployeePosition.employee_id == employee_id,
                EmployeePosition.start_date <= today,
                or_(
                    EmployeePosition.end_date.is_(None),
                    EmployeePosition.end_date >= today
                )
            )
            .values(**update_values)
        )
        await self.db.execute(stmt)
        await self.db.flush()

    @staticmethod
    def _extract_dept_code(dept: Optional[Department], fallback: str = "00") -> str:
        """Извлекает числовой/буквенный код подразделения из number или code, избегая наименований."""
        if not dept:
            return fallback

        # Проверяем атрибуты code или number (в зависимости от вашей ORM-модели)
        code_val = getattr(dept, 'number', None) or getattr(dept, 'code', None)

        if code_val is not None and str(code_val).strip():
            return str(code_val).strip()

        return fallback

    async def get_department_codes_for_employee(self, employee_id: int) -> tuple[str, str]:
        """
        Возвращает (код_родительского_подразделения, код_отдела) для сотрудника.
        """
        today = date.today()
        stmt = (
            select(Department)
            .join(EmployeePosition, EmployeePosition.department_id == Department.id)
            .where(
                EmployeePosition.employee_id == employee_id,
                EmployeePosition.start_date <= today,
                or_(
                    EmployeePosition.end_date.is_(None),
                    EmployeePosition.end_date >= today
                )
            )
            .order_by(EmployeePosition.start_date.desc())
        )
        result = await self.db.execute(stmt)
        dept = result.scalars().first()

        if not dept:
            return "00", "00"

        # 1. Получаем код текущего отдела
        sub_dept_code = self._extract_dept_code(dept, fallback="00")

        # 2. Ищем родительское подразделение на 1 шаг выше
        top_dept_code = sub_dept_code

        if hasattr(dept, 'hierarchy_path') and dept.hierarchy_path:
            # Массив ID от корня к текущему, например: ["1", "15", "42"]
            path_ids = [int(p) for p in dept.hierarchy_path.split('/') if p.isdigit()]

            # Нам нужен родитель — элемент, стоящий прямо перед текущим отделом
            if len(path_ids) > 1:
                # Берем предпоследний ID (на шаг выше)
                parent_dept_id = path_ids[-2]

                top_res = await self.db.execute(
                    select(Department).where(Department.id == parent_dept_id)
                )
                parent_dept = top_res.scalar_one_or_none()
                top_dept_code = self._extract_dept_code(parent_dept, fallback=sub_dept_code)
        elif getattr(dept, 'parent_id', None) is not None:
            # Альтернативный фоллбэк через parent_id, если hierarchy_path не заполнен
            top_res = await self.db.execute(
                select(Department).where(Department.id == dept.parent_id)
            )
            parent_dept = top_res.scalar_one_or_none()
            top_dept_code = self._extract_dept_code(parent_dept, fallback=sub_dept_code)

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
        """Возвращает уникальных сотрудников организации с жадной загрузкой их активных должностей."""
        today = date.today()
        stmt = (
            select(Employee)
            .options(
                selectinload(
                    Employee.positions.and_(
                        EmployeePosition.start_date <= today,
                        or_(
                            EmployeePosition.end_date.is_(None),
                            EmployeePosition.end_date >= today
                        )
                    )
                )
            )
            .distinct()
            .join(EmployeePosition, EmployeePosition.employee_id == Employee.id)
            .join(Department, Department.id == EmployeePosition.department_id)
            .where(
                Department.organization_id == org_id,
                Employee.is_active.is_(True),
                EmployeePosition.start_date <= today,
                or_(
                    EmployeePosition.end_date.is_(None),
                    EmployeePosition.end_date >= today
                )
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def search_organizations(self, pattern: str, limit: int = 10) -> list[Organization]:
        stmt = (
            select(Organization)
            .where(Organization.name.ilike(pattern))
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def search_departments(self, pattern: str, limit: int = 10) -> list[Department]:
        stmt = (
            select(Department)
            .where(Department.name.ilike(pattern))
            .limit(limit)
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def search_employees(
            self,
            pattern: str,
            limit: int = 10,
            include_positions: bool = True
    ) -> list[Employee]:
        """
        Поиск сотрудников по ФИО с предзагрузкой активных должностей.
        """
        today = date.today()

        stmt = select(Employee).where(
            or_(
                Employee.last_name.ilike(pattern),
                Employee.first_name.ilike(pattern),
                Employee.patronymic.ilike(pattern)
            ),
            Employee.is_active.is_(True)
        )

        if include_positions:
            stmt = stmt.options(
                selectinload(
                    Employee.positions.and_(
                        EmployeePosition.start_date <= today,
                        or_(
                            EmployeePosition.end_date.is_(None),
                            EmployeePosition.end_date >= today
                        )
                    )
                )
            )

        stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())