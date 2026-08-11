from fastapi import HTTPException, status

from server.app.repositories.org_repo import OrgRepository

from server.app.schemas.org import DepartmentNode, OrganizationUpdate, OrganizationRead, OrganizationCreate
from server.app.schemas.user_schemas.employee_dto import CurrentUser

from server.app.services.common.security_service import SecurityService


class OrgService:
    def __init__(self, repo: OrgRepository, security: SecurityService):
        self.repo = repo
        self.security = security

    async def get_org_structure(self, org_id: int) -> list[DepartmentNode]:
        depts = await self.repo.get_departments_by_org(org_id)

        nodes = {
            d.id: DepartmentNode(
                id=d.id,
                name=d.name,
                type_name=d.department_type.name if d.department_type else None,
            )
            for d in depts
        }
        root_nodes = []

        for d in depts:
            node = nodes[d.id]
            if d.parent_id is None:
                root_nodes.append(node)
            elif d.parent_id in nodes:
                nodes[d.parent_id].children.append(node)

        return root_nodes

    async def update_organization(
        self, current_user: CurrentUser, org_id: int, data: OrganizationUpdate
    ) -> OrganizationRead:
        # 1. Проверяем права на управление организацией
        if not await self.security.can_manage_org(current_user, org_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на редактирование этой организации",
            )

        # 2. Проверяем существование организации ДО обновления
        existing_org = await self.repo.get_organization_by_id(org_id)
        if not existing_org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Организация не найдена",
            )

        # 3. Валидируем наличие передаваемых полей
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нет данных для обновления",
            )

        await self.repo.update_organization(org_id, update_data)

        updated_org = await self.repo.get_organization_by_id(org_id)
        return OrganizationRead.model_validate(updated_org)

    async def create_organization(
        self, current_user: CurrentUser, data: OrganizationCreate
    ) -> OrganizationRead:
        # 1. Синхронный метод is_admin — вызываем БЕЗ await
        if not self.security.is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав: требуется роль администратора",
            )

        # 2. Проверяем уникальность УНП
        existing_org = await self.repo.get_organization_by_unp(data.unp)
        if existing_org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Организация с таким УНП уже существует",
            )

        new_org = await self.repo.create_organization(data)
        return OrganizationRead.model_validate(new_org)

    async def get_all_organizations(
        self, limit: int = 100, offset: int = 0
    ) -> list[OrganizationRead]:
        orgs = await self.repo.get_all_organizations(limit=limit, offset=offset)
        return [OrganizationRead.model_validate(o) for o in orgs]

    async def get_organization_by_id(self, org_id: int) -> OrganizationRead:
        org = await self.repo.get_organization_by_id(org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Организация не найдена",
            )
        return OrganizationRead.model_validate(org)

    async def delete_organization(
        self, current_user: CurrentUser, org_id: int
    ) -> None:
        # 1. Синхронный метод is_admin — вызываем БЕЗ await
        if not self.security.is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав: требуется роль администратора",
            )

        org = await self.repo.get_organization_by_id(org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Организация не найдена",
            )

        # 2. Проверка связей перед удалением
        if await self.repo.has_linked_entities(org_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя удалить организацию, у которой есть привязанные подразделения",
            )

        await self.repo.delete_organization(org_id)

