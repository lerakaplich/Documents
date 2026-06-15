from fastapi import HTTPException

from server.app.repositories.employee_repo import EmployeesRepository
from server.app.repositories.org_repo import OrgRepository
from typing import List, Optional

from server.app.schemas.org import DepartmentNode, OrganizationUpdate, OrganizationRead, DepartmentUpdate, \
    DepartmentRead, DepartmentCreate
from server.app.schemas.user_schemas.employee_dto import CurrentUser

from server.app.services.security_service import SecurityService

class DepartmentService:
    def __init__(self, repo: OrgRepository, emp_repo: EmployeesRepository, security: SecurityService):
        self.repo = repo
        self.emp_repo = emp_repo
        self.security = security

    async def create_department(self, current_user: CurrentUser, data: DepartmentCreate) -> DepartmentRead:
        # 1. Проверка прав: используем SecurityService
        if data.parent_id:
            await self.security.verify_dept_access(current_user, data.parent_id)
        else:
            await self.security.verify_is_admin(current_user)

        # 2. Валидация родителя
        parent_path = ""
        if data.parent_id:
            parent = await self.repo.get_department_by_id(data.parent_id)
            if not parent:
                raise HTTPException(status_code=404, detail="Родитель не найден")
            parent_path = parent.hierarchy_path

        # 3. Создание (используем транзакцию, чтобы path не остался пустым при ошибке)
        async with self.repo.db.begin_nested():
            new_dept = await self.repo.create_department(data)
            new_path = f"{parent_path}/{new_dept.id}".strip("/")
            await self.repo.update_path(new_dept.id, new_path)

        return DepartmentRead.model_validate(new_dept)

    async def update_department(self, current_user: CurrentUser, dept_id: int,
                                data: DepartmentUpdate) -> DepartmentRead:
        # 1. Проверка прав (иерархическая)
        await self.security.verify_dept_access(current_user, dept_id)

        # 2. Подготовка данных
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="Нет данных для обновления")

        # 3. Обновление
        updated_dept = await self.repo.update_department(dept_id, update_data)
        if not updated_dept:
            raise HTTPException(status_code=404, detail="Подразделение не найдено")

        return DepartmentRead.model_validate(updated_dept)

    async def set_department_head(self, user: CurrentUser, dept_id: int, employee_id: int):
        # 1. Проверка прав (остается внешней, вне транзакции)
        await self.security.verify_can_appoint_leader(user, dept_id)

        # 2. Атомарная транзакция для бизнес-логики
        async with self.repo.db.begin_nested():
            # Сначала обновляем руководителя
            await self.repo.update_department_head(dept_id, employee_id)

            # Выдаем технические права
            pos = await self.emp_repo.get_position_by_employee_and_dept(employee_id, dept_id)

            # Если позиции нет, возможно, стоит выбросить ошибку?
            # Или пропустить? Обычно лучше знать, если что-то пошло не так.
            if not pos:
                raise HTTPException(status_code=404, detail="Сотрудник не состоит в этом отделе")

            await self.emp_repo.update_is_leader(pos.id, True)

        return {"message": "Руководитель успешно назначен"}

    async def remove_department_head(self, user: CurrentUser, dept_id: int):
        # 1. Проверка прав (кто может снимать руководителя)
        await self.security.verify_can_appoint_leader(user, dept_id)

        # 2. Получаем департамент
        dept = await self.repo.get_department_by_id(dept_id)
        if not dept or not dept.head_employee_id:
            raise HTTPException(status_code=400, detail="Руководитель не назначен")

        # 3. Снимаем технические права (is_leader = False)
        # Прямая работа с emp_repo, так как это логика синхронизации
        pos = await self.emp_repo.get_position_by_employee_and_dept(dept.head_employee_id, dept_id)
        if pos:
            await self.emp_repo.update_is_leader(pos.id, False)

        # 4. Обнуляем руководителя
        await self.repo.update_department_head(dept_id, None)

        return {"message": "Руководитель успешно снят с должности"}

    async def delete_department(self, user: CurrentUser, dept_id: int):
        # 1. Проверка прав
        await self.security.verify_can_appoint_leader(user, dept_id)

        # 2. Проверка детей
        if await self.repo.has_children(dept_id):
            raise HTTPException(status_code=400, detail="Нельзя удалить отдел, у которого есть дочерние подразделения")

        # 3. Проверка сотрудников (важный этап!)
        employees = await self.repo.get_employees_by_dept(dept_id)
        if employees:
            raise HTTPException(status_code=400, detail="Нельзя удалить отдел, в котором числятся сотрудники")

        # 4. Удаление
        await self.repo.delete_department(dept_id)
        return {"message": "Подразделение успешно удалено"}

    async def move_department(self, user: CurrentUser, dept_id: int, new_parent_id: Optional[int]):
        if new_parent_id is None:
            raise HTTPException(status_code=400, detail="Подразделение должно иметь родителя")

        await self.security.verify_can_appoint_leader(user, dept_id)

        # 1. Получаем нового родителя (чтобы узнать его путь)
        new_parent_path = ""
        if new_parent_id:
            new_parent_path = await self.repo.get_dept_path_by_id(new_parent_id) or ""

        # 2. Пересчитываем путь для перемещаемого отдела
        new_path = f"{new_parent_path}/{dept_id}".strip("/")

        async with self.repo.db.begin_nested():
            # Обновляем сам отдел
            await self.repo.update_parent(dept_id, new_parent_id)
            await self.repo.update_path(dept_id, new_path)

            # 3. Рекурсивное обновление потомков (если они есть)
            descendants = await self.repo.get_all_descendants(dept_id)
            for d in descendants:
                if d.id == dept_id: continue
                # Логика: заменяем старую часть пути на новую
                # Это требует внимательности при работе со строками
                old_path_part = await self.repo.get_dept_path_by_id(dept_id)
                new_d_path = d.hierarchy_path.replace(old_path_part, new_path)
                await self.repo.update_path(d.id, new_d_path)

        return {"message": "Подразделение перемещено"}

    async def get_department_by_id(self, dept_id: int) -> DepartmentRead:
        dept = await self.repo.get_department_detail(dept_id)
        if not dept:
            raise HTTPException(
                status_code=404,
                detail=f"Подразделение с ID {dept_id} не найдено"
            )
        return DepartmentRead.model_validate(dept)

    async def archive_department(self, user: CurrentUser, dept_id: int):
        # 1. Проверка прав (кто может архивировать)
        # Только глобальные админы или вышестоящее руководство
        await self.security.verify_can_appoint_leader(user, dept_id)

        # 2. Проверка: есть ли там сотрудники? (бизнес-логика)
        employees = await self.repo.get_employees_by_dept(dept_id)
        if employees:
            raise HTTPException(status_code=400, detail="Нельзя архивировать отдел, в котором есть сотрудники")

        # 3. Архивируем
        await self.repo.update_department(dept_id, {"is_active": False})
        return {"message": "Подразделение успешно архивировано"}
