from fastapi import HTTPException

from server.app.repositories.employee_repo import EmployeesRepository
from server.app.repositories.org_repo import OrgRepository
from pydantic import BaseModel
from typing import List, Optional

from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.schemas.user_schemas.org_dto import DepartmentNode, DepartmentCreate, DepartmentRead, \
    OrganizationUpdate, OrganizationRead, DepartmentUpdate
from server.app.services.security_service import SecurityService


class OrgService:
    def __init__(self, repo: OrgRepository, emp_repo: EmployeesRepository, security: SecurityService):
        self.repo = repo
        self.emp_repo = emp_repo # Добавляем это
        self.security = security

    async def get_org_structure(self, org_id: int) -> List[DepartmentNode]:
        depts = await self.repo.get_departments_by_org(org_id)

        nodes = {
            d.id: DepartmentNode(
                id=d.id,
                name=d.name,
                type_name=d.department_type.name if d.department_type else None
            ) for d in depts
        }
        root_nodes = []

        for d in depts:
            node = nodes[d.id]
            if d.parent_id is None:
                root_nodes.append(node)
            else:
                if d.parent_id in nodes:
                    nodes[d.parent_id].children.append(node)

        return root_nodes

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

    async def update_organization(
            self,
            current_user: CurrentUser,
            org_id: int,
            data: OrganizationUpdate
    ) -> OrganizationRead:

        await self.security.verify_org_access(current_user, org_id)
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="Нет данных для обновления")

        await self.repo.update_organization(org_id, update_data)

        updated_org = await self.repo.get_organization_by_id(org_id)
        if not updated_org:
            raise HTTPException(status_code=404, detail="Организация не найдена")

        return OrganizationRead.model_validate(updated_org)

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

    async def delete_department(self, user: CurrentUser, dept_id: int):
        # Проверяем права так же строго
        await self.security.verify_can_appoint_leader(user, dept_id)

        # Жесткая проверка: нет ли детей (вложенных отделов)?
        if await self.repo.has_children(dept_id):
            raise HTTPException(status_code=400, detail="Нельзя удалить отдел, имеющий подразделения")

        await self.repo.delete_department(dept_id)
        return {"message": "Подразделение удалено"}