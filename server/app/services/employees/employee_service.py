from typing import List, Optional

from fastapi import HTTPException, status

from server.app.database.document_models import AppRights
from server.app.database.employee_models import EmployeePosition
from server.app.repositories.document_repo import DocumentRepository
from server.app.repositories.employee_repo import EmployeesRepository
from server.app.schemas.user_schemas.employee_dto import EmployeeRead, EmployeeListRead, CurrentUser, \
    EmployeeDetailRead, EmployeeCreate
from sqlalchemy.exc import IntegrityError


class EmployeeService:
    def __init__(self, repo: EmployeesRepository, doc_repo: DocumentRepository):
        self.repo = repo
        self.doc_repo = doc_repo

    async def get_staff_by_department(
        self,
        department_id: int,
        include_inactive: bool = False # Добавляем параметр
    ) -> List[EmployeeRead]:
        employees = await self.repo.get_by_department(department_id, include_inactive=include_inactive)
        return [EmployeeRead.model_validate(e) for e in employees]

    async def get_employees_list(self, page: int, limit: int, show_fired: bool):
        offset = (page - 1) * limit

        # Получаем данные из HR-базы
        employees_rows = await self.repo.get_paginated_employees(limit, offset, show_fired)

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

    async def can_view_employee(self, current_user: CurrentUser, target_emp_id: int) -> bool:
        # 1. Админы видят всё
        if current_user.rights in [AppRights.admin, AppRights.superadmin]:
            return True

        # 2. Получаем подразделения, где текущий пользователь - руководитель
        leader_dept_paths = await self.repo.get_leader_paths(current_user.id)

        # 3. Получаем подразделения целевого сотрудника
        target_dept_paths = await self.repo.get_target_dept_paths(target_emp_id)

        # 4. Проверка: является ли путь руководителя "префиксом" пути отдела сотрудника
        for leader_path in leader_dept_paths:
            for target_path in target_dept_paths:
                if target_path.startswith(leader_path):
                    return True
        return False

    async def get_full_employee_info(self, emp_id: int) -> Optional[EmployeeDetailRead]:
        employee = await self.repo.get_by_id(emp_id)
        if not employee:
            return None

        rights_data = await self.doc_repo.get_rights_map([emp_id])
        user_rights = rights_data.get(emp_id, "user")

        # Конвертируем ORM объект в словарь, добавляя туда права
        emp_dict = employee.__dict__.copy()
        emp_dict["rights"] = user_rights

        # Pydantic теперь получит все нужные поля, включая rights
        return EmployeeDetailRead.model_validate(emp_dict)

    async def create_employee(self, current_user: CurrentUser, data: EmployeeCreate):
        if not await self.can_manage_department(current_user, data.position.department_id):
            raise HTTPException(status_code=403, detail="Нет прав в этом подразделении")

        # 1. Выполняем все операции записи
        async with self.repo.db.begin():
            new_emp = await self.repo.add_employee(data)
            await self.repo.add_position(new_emp.id, data.position)

            await self.doc_repo.upsert_system_employee(
                id=new_emp.id,
                last_name=data.last_name,
                first_name=data.first_name,
                patronymic=data.patronymic or "",
                rights=data.rights
            )
            # Завершаем транзакцию здесь (выход из блока with)

        # 2. ЧИСТОЕ РЕШЕНИЕ: Запрашиваем объект обратно с сервера
        # с заранее подгруженными позициями (selectinload)
        return await self.repo.get_employee_with_positions(new_emp.id)

    async def can_manage_department(self, current_user: CurrentUser, target_dept_id: int) -> bool:
        # Админы управляют всем
        if current_user.rights in [AppRights.admin, AppRights.superadmin]:
            return True

        # Получаем пути подразделений, которыми текущий пользователь руководит
        leader_paths = await self.repo.get_leader_paths(current_user.id)

        # Получаем путь целевого подразделения
        target_path = await self.repo.get_dept_path_by_id(target_dept_id)

        if not target_path:
            return False

        # Руководитель может управлять, если его путь является префиксом пути целевого отдела
        return any(target_path.startswith(path) for path in leader_paths)