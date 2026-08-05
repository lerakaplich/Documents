from typing import Optional

from fastapi import HTTPException,status

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
        self, department_id: int, include_inactive: bool = False
    ) -> list[EmployeeRead]:
        employees = await self.emp_repo.get_by_department(
            department_id, include_inactive=include_inactive
        )
        return [EmployeeRead.model_validate(e) for e in employees]

    async def get_employees_list(
        self, page: int, limit: int, show_fired: bool
    ) -> list[EmployeeListRead]:
        offset = (page - 1) * limit

        # Получаем данные из HR-базы
        employees_rows = await self.emp_repo.get_paginated_employees(
            limit, offset, show_fired
        )

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
                rights=rights_map.get(r.id, "user"),
            )
            for r in employees_rows
        ]

    async def get_full_employee_info(
        self, current_user: CurrentUser, emp_id: int
    ) -> Optional[EmployeeDetailRead]:
        # 1. Проверка прав на просмотр профиля
        if not await self.security.can_view_employee(current_user, emp_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на просмотр данных этого сотрудника",
            )

        # 2. Получение данных
        employee = await self.emp_repo.get_by_id(emp_id)
        if not employee:
            return None

        # 3. Формирование DTO с ролями
        rights_data = await self.doc_repo.get_rights_map([emp_id])
        user_rights = rights_data.get(emp_id, "user")

        emp_dict = employee.__dict__.copy()
        emp_dict["rights"] = user_rights

        return EmployeeDetailRead.model_validate(emp_dict)

    async def create_employee(
        self, current_user: CurrentUser, data: EmployeeCreate
    ):
        # 1. Проверка прав на управление подразделением, куда добавляется сотрудник
        if not await self.security.can_manage_dept(
            current_user, data.position.department_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на добавление сотрудников в данное подразделение",
            )

        async with self.emp_repo.db.begin():
            new_emp = await self.emp_repo.add_employee(data)
            await self.emp_repo.add_position(
                new_emp.id,
                data.position.department_id,
                data.position.position_name,
                data.position.is_leader,
            )
            await self.doc_repo.upsert_system_employee(
                id=new_emp.id,
                last_name=data.last_name,
                first_name=data.first_name,
                patronymic=data.patronymic or "",
                rights=data.rights,
            )

        return await self.emp_repo.get_employee_with_positions(new_emp.id)

    async def update_own_profile(self, user_id: int, data: EmployeeProfileUpdate):
        update_dict = data.model_dump(exclude_unset=True)
        if not update_dict:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нет данных для обновления",
            )

        await self.emp_repo.update_employee_profile(user_id, update_dict)
        return await self.emp_repo.get_by_id(user_id)

    async def update_employee_by_manager(
        self,
        manager_user: CurrentUser,
        target_id: int,
        data: EmployeeFullUpdate,
    ):
        # 1. Проверка доступа к сотруднику
        if not await self.security.can_view_employee(manager_user, target_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на редактирование этого сотрудника",
            )

        # 2. Проверка эскалации прав (если менеджер меняет поле 'rights')
        if data.rights is not None:
            if not self.security.can_update_rights(
                manager_user, data.rights
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Недостаточно прав для назначения указанного уровня доступа",
                )

        # 3. Получение текущих данных
        current_emp = await self.emp_repo.get_by_id(target_id)
        current_sys = await self.doc_repo.get_system_employee_by_id(target_id)
        if not current_emp or not current_sys:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Сотрудник не найден",
            )

        # 4. Проверка переводов (если меняются позиции)
        if data.positions is not None:
            current_positions = await self.emp_repo.get_positions_by_employee(
                target_id
            )
            current_dept_ids = {p.department_id for p in current_positions}

            for pos in data.positions:
                if pos.department_id not in current_dept_ids:
                    if not await self.security.can_manage_dept(
                        manager_user, pos.department_id
                    ):
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail=f"Нет прав на перевод сотрудника в подразделение ID {pos.department_id}",
                        )

        # 5. Выполнение обновлений в транзакции
        async with self.emp_repo.db.begin_nested():
            update_data = data.model_dump(
                exclude={
                    "positions",
                    "rights",
                    "last_name",
                    "first_name",
                    "patronymic",
                },
                exclude_unset=True,
            )
            if update_data:
                await self.emp_repo.update_employee_profile(
                    target_id, update_data
                )

            if data.positions is not None:
                await self.sync_employee_positions(target_id, data.positions)

            new_rights = (
                data.rights if data.rights is not None else current_sys.rights
            )

            await self.doc_repo.upsert_system_employee(
                id=target_id,
                last_name=data.last_name or current_emp.last_name,
                first_name=data.first_name or current_emp.first_name,
                patronymic=data.patronymic
                if data.patronymic is not None
                else current_emp.patronymic,
                rights=new_rights,
            )

        updated_emp = await self.emp_repo.get_employee_with_positions(target_id)
        result = updated_emp.__dict__.copy()
        result["rights"] = data.rights or current_sys.rights
        return EmployeeDetailRead.model_validate(result)

    async def sync_employee_positions(
        self, employee_id: int, new_positions: list[PositionUpdate]
    ):
        current_positions = await self.emp_repo.get_positions_by_employee(
            employee_id
        )
        current_map = {p.id: p for p in current_positions}
        new_ids = {p.id for p in new_positions if p.id is not None}

        # Удаляем те, которых больше нет в запросе
        for p_id in current_map:
            if p_id not in new_ids:
                await self.emp_repo.delete_position(p_id)

        # Добавляем или обновляем
        for pos_data in new_positions:
            if pos_data.id and pos_data.id in current_map:
                await self.emp_repo.update_position(pos_data)
            else:
                await self.emp_repo.add_position(
                    employee_id,
                    pos_data.department_id,
                    pos_data.position_name,
                    pos_data.is_leader,
                )

    async def add_employee_position(
            self, current_user: CurrentUser, emp_id: int, data: PositionCreate
    ):
        # 1. Проверка прав на указанное подразделение
        if not await self.security.can_manage_dept(
                current_user, data.department_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на добавление должности в данном подразделении",
            )

        # 2. Добавление через явный разбор полей DTO
        return await self.emp_repo.add_position(
            employee_id=emp_id,
            dept_id=data.department_id,
            name=data.position_name,
            is_leader=data.is_leader,
        )

    async def remove_employee_position(
        self, current_user: CurrentUser, emp_id: int, pos_id: int
    ):
        # 1. Проверка количества позиций (бизнес-правило)
        positions = await self.emp_repo.get_positions_by_employee(emp_id)
        if len(positions) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя удалить единственную должность сотрудника",
            )

        # 2. Поиск позиции
        pos_to_delete = next((p for p in positions if p.id == pos_id), None)
        if not pos_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Должность не найдена",
            )

        # 3. Проверка прав на отдел удаляемой должности
        if not await self.security.can_manage_dept(
            current_user, pos_to_delete.department_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на удаление должности в этом подразделении",
            )

        return await self.emp_repo.delete_position(pos_id)

    async def set_access_leadership(
        self, user: CurrentUser, pos_id: int, is_leader: bool
    ):
        # 1. Поиск должности
        pos = await self.emp_repo.get_position_by_id(pos_id)
        if not pos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Должность не найдена",
            )

        # 2. Проверка прав
        if not await self.security.can_manage_dept(user, pos.department_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на изменение статуса руководителя в этом подразделении",
            )

        # 3. Обновление флага
        return await self.emp_repo.update_is_leader(pos_id, is_leader)
