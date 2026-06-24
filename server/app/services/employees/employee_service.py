from typing import List, Optional

from fastapi import HTTPException

from server.app.repositories.document_repo import DocumentRepository
from server.app.repositories.employee_repo import EmployeesRepository
from server.app.repositories.org_repo import OrgRepository
from server.app.schemas.user_schemas.employee_dto import EmployeeRead, EmployeeListRead, CurrentUser, \
    EmployeeDetailRead, EmployeeCreate, EmployeeProfileUpdate, EmployeeFullUpdate, PositionCreate, \
    PositionUpdate
from server.app.services.common.security_service import SecurityService


class EmployeeService:
    def __init__(self, repo: EmployeesRepository, doc_repo: DocumentRepository, org_repo: OrgRepository, security: SecurityService):
        self.emp_repo = repo
        self.org_repo = org_repo
        self.doc_repo = doc_repo
        self.security = security # Внедряем сервис прав

    async def get_staff_by_department(
        self,
        department_id: int,
        include_inactive: bool = False # Добавляем параметр
    ) -> List[EmployeeRead]:
        employees = await self.emp_repo.get_by_department(department_id, include_inactive=include_inactive)
        return [EmployeeRead.model_validate(e) for e in employees]

    async def get_employees_list(self, page: int, limit: int, show_fired: bool):
        offset = (page - 1) * limit

        # Получаем данные из HR-базы
        employees_rows = await self.emp_repo.get_paginated_employees(limit, offset, show_fired)

        # Получаем права из БД документов
        emp_ids = [r.id for r in employees_rows]
        rights_map = await self.doc_repo.get_rights_map(emp_ids)

        return [
            EmployeeListRead(
                id=r.id,
                full_name=r.full_name,
                position_name=r.position_name,
                department_name=r.department_name,
                phone_number=r.phone_number,
                rights=rights_map.get(r.id, "user")
            ) for r in employees_rows
        ]

    async def get_full_employee_info(self, current_user: CurrentUser, emp_id: int) -> Optional[EmployeeDetailRead]:
        # 1. Сначала проверяем права!
        await self.security.verify_employee_view_access(current_user, emp_id)

        # 2. Потом берем данные
        employee = await self.emp_repo.get_by_id(emp_id)
        if not employee:
            return None

        # 3. Собираем объект
        rights_data = await self.doc_repo.get_rights_map([emp_id])
        user_rights = rights_data.get(emp_id, "user")

        # Использование .model_dump() ORM-объекта (через SQLAlchemy Pydantic-плагин или просто словарем)
        emp_dict = employee.__dict__.copy()
        emp_dict["rights"] = user_rights

        return EmployeeDetailRead.model_validate(emp_dict)

    async def create_employee(self, current_user: CurrentUser, data: EmployeeCreate):
        # Одной строкой проверяем права
        await self.security.verify_dept_access(current_user, data.position.department_id)

        async with self.emp_repo.db.begin():
            new_emp = await self.emp_repo.add_employee(data)
            await self.emp_repo.add_position(
                new_emp.id,
                data.department_id,
                data.position_name,
                data.is_leader
            )
            await self.doc_repo.upsert_system_employee(
                id=new_emp.id,
                last_name=data.last_name,
                first_name=data.first_name,
                patronymic=data.patronymic or "",
                rights=data.rights
            )
        return await self.emp_repo.get_employee_with_positions(new_emp.id)

    async def update_own_profile(self, user_id: int, data: EmployeeProfileUpdate):
        update_dict = data.model_dump(exclude_unset=True)
        if not update_dict:
            raise HTTPException(status_code=400, detail="Нет данных для обновления")

        await self.emp_repo.update_employee_profile(user_id, update_dict)

        return await self.emp_repo.get_by_id(user_id)

    async def update_employee_by_manager(
            self,
            manager_user: CurrentUser,
            target_id: int,
            data: EmployeeFullUpdate
    ):
        # 1. Проверка доступа к сотруднику (Иерархическая)
        await self.security.verify_employee_view_access(manager_user, target_id)

        # 2. Проверка эскалации прав (если менеджер меняет поле 'rights')
        # Важно: если rights нет в данных (None), проверку пропускаем
        if data.rights is not None:
            await self.security.verify_can_update_rights(manager_user, data.rights)

        # 3. Получение текущих данных
        current_emp = await self.emp_repo.get_by_id(target_id)
        current_sys = await self.doc_repo.get_system_employee_by_id(target_id)
        if not current_emp or not current_sys:
            raise HTTPException(status_code=404, detail="Сотрудник не найден")

        # 4. Проверка переводов (если меняются позиции)
        if data.positions is not None:
            current_positions = await self.emp_repo.get_positions_by_employee(target_id)
            current_dept_ids = {p.department_id for p in current_positions}

            for pos in data.positions:
                # Если отдел новый (или id отсутствует, значит новая позиция) — проверяем доступ
                if pos.department_id not in current_dept_ids:
                    await self.security.verify_dept_access(manager_user, pos.department_id)

        # 5. Выполнение обновлений в транзакции
        async with self.emp_repo.db.begin_nested():
            # А. Обновление профиля в HR базе (все кроме прав, ФИО и позиций)
            update_data = data.model_dump(
                exclude={"positions", "rights", "last_name", "first_name", "patronymic"},
                exclude_unset=True
            )
            if update_data:
                await self.emp_repo.update_employee_profile(target_id, update_data)

            # Б. Синхронизация должностей
            if data.positions is not None:
                await self.sync_employee_positions(target_id, data.positions)

            # В. Синхронизация с системой документов (ФИО + ПРАВА)
            # Если data.rights пришло None, берем текущие из системы (current_sys.rights)
            new_rights = data.rights if data.rights is not None else current_sys.rights

            await self.doc_repo.upsert_system_employee(
                id=target_id,
                last_name=data.last_name or current_emp.last_name,
                first_name=data.first_name or current_emp.first_name,
                patronymic=data.patronymic if data.patronymic is not None else current_emp.patronymic,
                rights=new_rights
            )

        # 6. Чтение обновленного объекта для ответа
        updated_emp = await self.emp_repo.get_employee_with_positions(target_id)

        # Конвертация для ответа (включая права из системы)
        result = updated_emp.__dict__.copy()
        result["rights"] = data.rights or current_sys.rights
        return EmployeeDetailRead.model_validate(result)

    async def sync_employee_positions(self, employee_id: int, new_positions: List[PositionUpdate]):
        # 1. Получаем текущие позиции
        current_positions = await self.emp_repo.get_positions_by_employee(employee_id)
        current_map = {p.id: p for p in current_positions}
        new_ids = {p.id for p in new_positions if p.id is not None}

        # 2. Удаляем те, которых больше нет в запросе
        for p_id in current_map:
            if p_id not in new_ids:
                await self.emp_repo.delete_position(p_id)

        # 3. Добавляем или обновляем
        for pos_data in new_positions:
            if pos_data.id and pos_data.id in current_map:
                # Проверяем, изменились ли данные, чтобы не делать лишний апдейт
                await self.emp_repo.update_position(pos_data)
            else:
                # Новая запись
                await self.emp_repo.add_position(
                    employee_id,
                    pos_data.department_id,
                    pos_data.position_name,
                    pos_data.is_leader
                )

    async def add_employee_position(self, current_user: CurrentUser, emp_id: int, data: PositionCreate):
        # 1. Проверка прав через SecurityService
        await self.security.verify_dept_access(current_user, data.department_id)

        # 2. Добавление
        return await self.emp_repo.add_position(emp_id, data)

    async def remove_employee_position(self, current_user: CurrentUser, emp_id: int, pos_id: int):
        # 1. Проверка количества позиций (бизнес-правило)
        positions = await self.emp_repo.get_positions_by_employee(emp_id)
        if len(positions) <= 1:
            raise HTTPException(status_code=400, detail="Нельзя удалить единственную должность")

        # 2. Поиск позиции и проверка прав на отдел, к которому она принадлежит
        pos_to_delete = next((p for p in positions if p.id == pos_id), None)
        if not pos_to_delete:
            raise HTTPException(status_code=404, detail="Позиция не найдена")

        # Проверка через SecurityService (вместо старого метода)
        await self.security.verify_dept_access(current_user, pos_to_delete.department_id)

        return await self.emp_repo.delete_position(pos_id)

    async def set_access_leadership(self, user: CurrentUser, pos_id: int, is_leader: bool):
        # 1. Проверяем доступ к отделу
        pos = await self.emp_repo.get_position_by_id(pos_id)
        await self.security.verify_dept_access(user, pos.department_id)

        # 2. Просто меняем флаг
        return await self.emp_repo.update_is_leader(pos_id, is_leader)
