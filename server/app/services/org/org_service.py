import logging
import math

from fastapi import HTTPException, status

from server.app.repositories.employee_repo import EmployeesRepository
from server.app.repositories.org_repo import OrgRepository

from server.app.schemas.org import DepartmentNode, OrganizationUpdate, OrganizationRead, OrganizationCreate
from server.app.schemas.user_schemas.employee_dto import CurrentUser, EmployeeRead

from server.app.services.common.security_service import SecurityService

logger = logging.getLogger(__name__)


class OrgService:
    def __init__(
        self,
        repo: OrgRepository,
        emp_repo: EmployeesRepository,
        security: SecurityService
    ):
        self.repo = repo
        self.emp_repo = emp_repo
        self.security = security

    async def get_organization_employees(
        self, current_user: CurrentUser, org_id: int
    ) -> list[EmployeeRead]:
        org = await self.repo.get_organization_by_id(org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Организация не найдена",
            )

        employees = await self.emp_repo.get_employees_by_org_id(org_id)
        return [EmployeeRead.model_validate(e) for e in employees]

    async def get_org_employees_short(
            self,
            org_id: int,
            show_fired: bool = False,
            page: int = 1,
            size: int = 20
    ) -> dict:
        logger.info(
            "Fetching short employee list for organization",
            extra={"org_id": org_id, "page": page, "size": size, "show_fired": show_fired}
        )

        # Проверка существования организации
        org = await self.repo.get_organization_by_id(org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Организация не найдена"
            )

        rows, total = await self.emp_repo.get_short_by_org_id_paginated(
            org_id=org_id,
            show_fired=show_fired,
            page=page,
            size=size
        )

        items = []
        for row in rows:
            patronymic_str = f" {row.patronymic}" if row.patronymic else ""
            items.append({
                "id": row.id,
                "full_name": f"{row.last_name} {row.first_name}{patronymic_str}".strip()
            })

        pages = math.ceil(total / size) if total > 0 else 1

        logger.info(
            "Successfully fetched short employee list for organization",
            extra={"org_id": org_id, "count": len(items), "total": total}
        )

        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": pages
        }

    async def get_org_structure(self, org_id: int) -> list[DepartmentNode]:
        org = await self.repo.get_organization_by_id(org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Организация не найдена",
            )

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
        if not await self.security.can_manage_org(current_user, org_id):
            logger.warning(
                "Access denied for organization update",
                extra={"user_id": current_user.id, "org_id": org_id},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет прав на редактирование этой организации",
            )

        existing_org = await self.repo.get_organization_by_id(org_id)
        if not existing_org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Организация не найдена",
            )

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нет данных для обновления",
            )

        await self.repo.update_organization(org_id, update_data)
        logger.info(
            "Organization updated",
            extra={"org_id": org_id, "user_id": current_user.id},
        )

        updated_org = await self.repo.get_organization_by_id(org_id)
        return OrganizationRead.model_validate(updated_org)

    async def create_organization(
        self, current_user: CurrentUser, data: OrganizationCreate
    ) -> OrganizationRead:
        if not self.security.is_admin(current_user):
            logger.warning(
                "Non-admin user attempted to create organization",
                extra={"user_id": current_user.id},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав: требуется роль администратора",
            )

        existing_org = await self.repo.get_organization_by_unp(data.unp)
        if existing_org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Организация с таким УНП уже существует",
            )

        new_org = await self.repo.create_organization(data)
        logger.info(
            "Organization created",
            extra={"org_id": new_org.id, "user_id": current_user.id},
        )
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
        if not self.security.is_admin(current_user):
            logger.warning(
                "Non-admin user attempted to delete organization",
                extra={"user_id": current_user.id, "org_id": org_id},
            )
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

        if await self.repo.has_linked_entities(org_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Нельзя удалить организацию, у которой есть привязанные подразделения",
            )

        await self.repo.delete_organization(org_id)
        logger.info(
            "Organization deleted",
            extra={"org_id": org_id, "user_id": current_user.id},
        )

