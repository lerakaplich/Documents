from fastapi import HTTPException

from server.app.repositories.employee_repo import EmployeesRepository
from server.app.repositories.org_repo import OrgRepository
from typing import List, Optional

from server.app.schemas.org import DepartmentNode, OrganizationUpdate, OrganizationRead, DepartmentUpdate, \
    DepartmentRead, DepartmentCreate
from server.app.schemas.user_schemas.employee_dto import CurrentUser

from server.app.services.security_service import SecurityService


class OrgService:
    def __init__(self, repo: OrgRepository, security: SecurityService):
        self.repo = repo
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

