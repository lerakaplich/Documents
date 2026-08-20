from fastapi import APIRouter, Depends
from server.app.deps import get_dept_service, get_current_user, get_employee_service
from server.app.schemas.org import DepartmentRead, DepartmentCreate, DepartmentUpdate, DepartmentMove
from server.app.schemas.user_schemas.employee_dto import CurrentUser, EmployeeRead
from server.app.services.employees.employee_service import EmployeeService
from server.app.services.org.department_service import DepartmentService

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.post("",
             status_code=201,
             response_model=DepartmentRead)
async def create_department(
    data: DepartmentCreate,
    current_user: CurrentUser = Depends(get_current_user), # Добавляем зависимость
    service: DepartmentService = Depends(get_dept_service)
):
    """Создание нового подразделения с проверкой связей"""
    return await service.create_department(current_user, data)

@router.get("/{department_id}/staff", response_model=list[EmployeeRead])
async def get_department_staff(
    department_id: int,
    service: EmployeeService = Depends(get_employee_service)
):
    """Список сотрудников в конкретном подразделении"""
    return await service.get_staff_by_department(department_id)

@router.patch("/{dept_id}", response_model=DepartmentRead)
async def update_department(
    dept_id: int,
    data: DepartmentUpdate,
    current_user: CurrentUser = Depends(get_current_user), # Добавили зависимость!
    service: DepartmentService = Depends(get_dept_service)
):
    return await service.update_department(current_user, dept_id, data)

@router.delete("/{dept_id}")
async def delete_department(
    dept_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: DepartmentService = Depends(get_dept_service)
):
    return await service.delete_department(current_user, dept_id)

@router.patch("/{department_id}/head")
async def update_department_head(
    department_id: int,
    new_head_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: DepartmentService = Depends(get_dept_service)
):
    return await service.set_department_head(current_user, department_id, new_head_id)

@router.delete("/{department_id}/head")
async def remove_department_head(
    department_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: DepartmentService = Depends(get_dept_service)
):
    return await service.remove_department_head(current_user, department_id)

@router.patch("/{dept_id}/move")
async def move_department(
    dept_id: int,
    data: DepartmentMove,
    current_user: CurrentUser = Depends(get_current_user),
    service: DepartmentService = Depends(get_dept_service)
):
    return await service.move_department(current_user, dept_id, data.new_parent_id)

@router.get("/{dept_id}", response_model=DepartmentRead)
async def get_department(
    dept_id: int,
    service: DepartmentService = Depends(get_dept_service)
):
    return await service.get_department_by_id(dept_id)