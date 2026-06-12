from fastapi import APIRouter, Depends, status
from typing import List

from server.app.deps import get_org_service, get_current_user
from server.app.role_checker import RoleChecker
from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.schemas.user_schemas.org_dto import DepartmentNode, DepartmentCreate, DepartmentUpdate, DepartmentRead, \
    OrganizationRead, OrganizationUpdate
from server.app.services.employees.org_service import OrgService
from server.app.database.document_models import AppRights

router = APIRouter(prefix="/org", tags=["Organization Structure"])

# CRUD операции
@router.get("/organizations/{org_id}/structure", response_model=List[DepartmentNode])
async def get_org_structure(org_id: int, service: OrgService = Depends(get_org_service)):
    return await service.get_org_structure(org_id)

@router.patch("/{org_id}", response_model=OrganizationRead)
async def update_org(
    org_id: int,
    data: OrganizationUpdate,
    service: OrgService = Depends(get_org_service)
):
    return await service.update_organization(org_id, data)

@router.post("/departments",
                 status_code=status.HTTP_201_CREATED,
                 response_model=DepartmentRead,
                 dependencies=[Depends(RoleChecker([AppRights.admin, AppRights.superadmin]))])

async def create_department(
    data: DepartmentCreate,
    service: OrgService = Depends(get_org_service)
):
    """Создание нового подразделения с проверкой связей"""
    return await service.create_department(data)

@router.patch("/departments/{dept_id}")
async def update_department(dept_id: int, data: DepartmentUpdate, service: OrgService = Depends(get_org_service)):
    return await service.update_department(dept_id, data)

@router.delete("/departments/{dept_id}")
async def delete_department(dept_id: int, service: OrgService = Depends(get_org_service)):
    return await service.delete_department(dept_id)

@router.patch("/departments/{department_id}/head")
async def update_department_head(
    department_id: int,
    new_head_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: OrgService = Depends(get_org_service) # Используем OrgService!
):
    return await service.set_department_head(current_user, department_id, new_head_id)