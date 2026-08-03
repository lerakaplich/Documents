from server.app.deps import get_org_service, get_current_user
from server.app.schemas.org import OrganizationRead, OrganizationUpdate, DepartmentNode, OrganizationCreate

from server.app.schemas.user_schemas.employee_dto import CurrentUser

from server.app.services.org.org_service import OrgService
from fastapi import APIRouter, Depends, status, Query
from typing import List

router = APIRouter(prefix="/org", tags=["Organization Structure"])

# CRUD операции
@router.post(
    "",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Создать новую организацию"
)
async def create_organization(
    data: OrganizationCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: OrgService = Depends(get_org_service)
):
    return await service.create_organization(current_user, data)


@router.get(
    "",
    response_model=List[OrganizationRead],
    summary="Получить список всех организаций"
)
async def get_all_organizations(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: OrgService = Depends(get_org_service)
):
    return await service.get_all_organizations(limit=limit, offset=offset)


@router.get(
    "/{org_id}",
    response_model=OrganizationRead,
    summary="Получить информацию об организации по ID"
)
async def get_organization(
    org_id: int,
    service: OrgService = Depends(get_org_service)
):
    return await service.get_organization_by_id(org_id)


@router.get(
    "/{org_id}/structure",
    response_model=List[DepartmentNode],
    summary="Получить древовидную структуру отделов организации"
)
async def get_org_structure(
    org_id: int,
    service: OrgService = Depends(get_org_service)
):
    return await service.get_org_structure(org_id)


@router.patch(
    "/{org_id}",
    response_model=OrganizationRead,
    summary="Обновить данные организации"
)
async def update_org(
    org_id: int,
    data: OrganizationUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: OrgService = Depends(get_org_service)
):
    return await service.update_organization(current_user, org_id, data)


@router.delete(
    "/{org_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить организацию"
)
async def delete_organization(
    org_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: OrgService = Depends(get_org_service)
):
    await service.delete_organization(current_user, org_id)