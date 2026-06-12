from fastapi import APIRouter, Depends

from server.app.api.employees import get_employee_service
from server.app.schemas.user_schemas.employee_dto import PositionCreate, CurrentUser
from server.app.services.employees.employee_service import EmployeeService
from server.app.deps import get_current_user

router = APIRouter(prefix="/employees/{employee_id}/positions", tags=["Positions"])

@router.post("")
async def add_position(
    employee_id: int,
    data: PositionCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: EmployeeService = Depends(get_employee_service)
):
    return await service.add_employee_position(current_user, employee_id, data)

@router.delete("/{position_id}")
async def delete_position(
    employee_id: int,
    position_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: EmployeeService = Depends(get_employee_service)
):
    return await service.remove_employee_position(current_user, employee_id, position_id)