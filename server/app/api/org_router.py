from fastapi import APIRouter, Depends, status
from typing import List

from server.app.api.employees import get_org_service
from server.app.schemas.user_schemas.org_dto import DepartmentNode, DepartmentCreate, DepartmentUpdate, DepartmentRead
from server.app.services.employees.org_service import OrgService
from server.app.database.document_models import AppRights
from server.app.deps import RoleChecker

router = APIRouter(prefix="/org", tags=["Organization Structure"])

# CRUD операции
@router.get("/organizations/{org_id}/structure", response_model=List[DepartmentNode])
async def get_org_structure(org_id: int, service: OrgService = Depends(get_org_service)):
    return await service.get_org_structure(org_id)

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