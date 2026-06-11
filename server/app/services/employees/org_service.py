from fastapi import HTTPException

from server.app.repositories.org_repo import OrgRepository
from pydantic import BaseModel
from typing import List, Optional

from server.app.schemas.user_schemas.org_dto import DepartmentNode, DepartmentCreate, DepartmentRead


class OrgService:
    def __init__(self, repo: OrgRepository):
        self.repo = repo

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

    async def create_department(self, data: DepartmentCreate) -> DepartmentRead:
        # 1. Валидация родителя
        parent_path = ""
        if data.parent_id:
            parent = await self.repo.get_department_by_id(data.parent_id)
            if not parent:
                raise HTTPException(status_code=404, detail="Родительское подразделение не найдено")

            if parent.organization_id != data.organization_id:
                raise HTTPException(status_code=400, detail="Ошибка организации")
            parent_path = parent.hierarchy_path

        # 2. Создаем запись
        new_dept = await self.repo.create_department(data)

        # 3. Путь
        new_path = f"{parent_path}/{new_dept.id}".strip("/")
        await self.repo.update_path(new_dept.id, new_path)

        return DepartmentRead.model_validate(new_dept)