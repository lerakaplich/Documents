from fastapi import APIRouter, Depends, status
from server.app.deps import get_current_user, get_overtime_service

from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.schemas.user_schemas.overtime_dto import OvertimeRead, OvertimeCreate, OvertimeUpdate

router = APIRouter(prefix="/overtime", tags=["Overtime"])

@router.post("", response_model=OvertimeRead, status_code=status.HTTP_201_CREATED)
async def create_overtime(
    data: OvertimeCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service = Depends(get_overtime_service)
):
    return await service.create_by_admin(current_user, data)

@router.patch("/{ot_id}/description")
async def update_my_description(
    ot_id: int,
    note: str,
    current_user: CurrentUser = Depends(get_current_user),
    service = Depends(get_overtime_service)
):
    return await service.update_note_by_employee(current_user, ot_id, note)

@router.patch("/{ot_id}")
async def admin_update_overtime(
    ot_id: int,
    data: OvertimeUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service = Depends(get_overtime_service)
):
    return await service.update_by_admin(current_user, ot_id, data)

@router.get("/my", response_model=list[OvertimeRead])
async def get_my_overtime(
    current_user: CurrentUser = Depends(get_current_user),
    service = Depends(get_overtime_service)
):
    return await service.get_by_employee(current_user, current_user.id)

@router.get("/department/{dept_id}", response_model=list[OvertimeRead])
async def get_dept_overtime(
    dept_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service = Depends(get_overtime_service)
):
    return await service.get_by_dept(current_user, dept_id)

@router.get("/all", response_model=list[OvertimeRead])
async def get_all_overtime(
    current_user: CurrentUser = Depends(get_current_user),
    service = Depends(get_overtime_service)
):
    return await service.get_all(current_user)

@router.delete("/{ot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_overtime(
    ot_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service = Depends(get_overtime_service)
):
    await service.delete_by_admin(current_user, ot_id)