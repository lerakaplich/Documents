from fastapi import HTTPException

from server.app.repositories.org_repo import OrgRepository
from pydantic import BaseModel
from typing import List, Optional

from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.schemas.user_schemas.org_dto import DepartmentNode, DepartmentCreate, DepartmentRead, \
    OrganizationUpdate, OrganizationRead, DepartmentUpdate
from server.app.services.security_service import SecurityService


class OrgService:
    def __init__(self, repo: OrgRepository, security: SecurityService):
        self.repo = repo
        self.security = security

    async def get_org_structure(self, org_id: int) -> List[DepartmentNode]:
        depts = await self.repo.get_departments_by_org(org_id)

        # Обновите DepartmentNode, добавив поле type_name: Optional[str]
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
        # 1. Проверка прав:
        if data.parent_id:
            # Если создаем внутри — проверяем доступ к родителю
            await self.security.verify_dept_access(current_user, data.parent_id)
        else:
            # Если создаем корень — только для администраторов
            await self.security.verify_is_admin(current_user)

        # 2. Валидация родителя (осталась как была)
        parent_path = ""
        if data.parent_id:
            parent = await self.repo.get_department_by_id(data.parent_id)
            if not parent:
                raise HTTPException(status_code=404, detail="Родитель не найден")
            parent_path = parent.hierarchy_path

        # 3. Создаем запись
        new_dept = await self.repo.create_department(data)
        new_path = f"{parent_path}/{new_dept.id}".strip("/")
        await self.repo.update_path(new_dept.id, new_path)

        return DepartmentRead.model_validate(new_dept)

    async def update_organization(self, current_user: CurrentUser, org_id: int,
                                  data: OrganizationUpdate) -> OrganizationRead:        # 1.

        await self.security.verify_org_access(current_user, org_id)
        # Подготовка данных (исключаем None)
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(status_code=400, detail="Нет данных для обновления")

        # 2. Выполнение обновления
        await self.repo.update_organization(org_id, update_data)

        # 3. Возвращаем обновленный объект
        updated_org = await self.repo.get_organization_by_id(org_id)
        if not updated_org:
            raise HTTPException(status_code=404, detail="Организация не найдена")

        return OrganizationRead.model_validate(updated_org)


    async def update_department(self, current_user: CurrentUser, dept_id: int,
                                data: DepartmentUpdate) -> DepartmentRead:
        # Проверяем доступ к отделу (используем иерархическую проверку)
        await self.security.verify_dept_access(current_user, dept_id)

        # Обновляем данные
        updated_dept = await self.repo.update_department(dept_id, data)
        return DepartmentRead.model_validate(updated_dept)

    async def set_department_head(self, user: CurrentUser, dept_id: int, employee_id: int):
        # 1. Проверка прав (используем SecurityService)
        await self.security.verify_can_appoint_leader(user, dept_id)

        # 2. Бизнес-логика назначения
        await self.repo.update_department_head(dept_id, employee_id)
        # Автоматически выдаем технические права (is_leader=True)
        # Находим позицию сотрудника в этом отделе
        pos = await self.emp_repo.get_position_by_employee_and_dept(employee_id, dept_id)
        if pos:
            await self.emp_repo.update_is_leader(pos.id, True)

    async def remove_department_head(self, user: CurrentUser, dept_id: int):
        await self.security.verify_can_appoint_leader(user, dept_id)
        if not await self.can_manage_department(current_user, department_id):
            raise HTTPException(status_code=403, detail="Нет прав на управление этим подразделением")

        # 2. Получаем текущего руководителя
        dept = await self.org_repo.get_department_by_id(department_id)
        if not dept or not dept.head_employee_id:
            raise HTTPException(status_code=400, detail="Руководитель не назначен")

        # 3. Снимаем технические права
        old_pos = await self.emp_repo.get_position_by_employee_and_dept(dept.head_employee_id, department_id)
        if old_pos:
            # Здесь мы используем current_user, чтобы set_access_leadership прошел проверку прав
            await self.set_access_leadership(current_user, dept.head_employee_id, old_pos.id, False)

        # 4. Обнуляем руководителя
        await self.emp_repo.update_department_head(department_id, None)

        return {"message": "Руководитель успешно снят с должности"}