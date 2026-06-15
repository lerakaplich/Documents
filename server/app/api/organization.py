from fastapi import APIRouter, Depends
from typing import List

from server.app.deps import get_org_service, get_current_user, get_dept_service
from server.app.schemas.org import OrganizationRead, OrganizationUpdate, DepartmentNode

from server.app.schemas.user_schemas.employee_dto import CurrentUser

from server.app.services.org.org_service import OrgService

router = APIRouter(prefix="/org", tags=["Organization Structure"])

# CRUD операции
@router.get("/organizations/{org_id}/structure", response_model=List[DepartmentNode])
async def get_org_structure(org_id: int, service: OrgService = Depends(get_org_service)):
    return await service.get_org_structure(org_id)

@router.patch("/{org_id}", response_model=OrganizationRead)
async def update_org(
    org_id: int,
    data: OrganizationUpdate, # FastAPI автоматически поймет, что это Body
    current_user: CurrentUser = Depends(get_current_user),
    service: OrgService = Depends(get_org_service)
):
    return await service.update_organization(current_user, org_id, data)
