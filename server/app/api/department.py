from fastapi import APIRouter, Depends, status, Body
from server.app.deps import get_dept_service, get_current_user, get_employee_service
from server.app.schemas.org import DepartmentRead, DepartmentCreate, DepartmentUpdate, DepartmentMove
from server.app.schemas.user_schemas.employee_dto import CurrentUser, EmployeeRead
from server.app.services.employees.employee_service import EmployeeService
from server.app.services.org.department_service import DepartmentService

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=DepartmentRead, summary="Создание подразделения")
async def create_department(
    data: DepartmentCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: DepartmentService = Depends(get_dept_service)
):
    """Создание нового подразделения с проверкой связей"""
    return await service.create_department(current_user, data)


@router.get("/{dept_id}", response_model=DepartmentRead, status_code=status.HTTP_200_OK, summary="Получить подразделение по ID")
async def get_department(
    dept_id: int,
    service: DepartmentService = Depends(get_dept_service)
):
    return await service.get_department_by_id(dept_id)


@router.get("/{department_id}/staff", response_model=list[EmployeeRead], status_code=status.HTTP_200_OK, summary="Сотрудники подразделения")
async def get_department_staff(
    department_id: int,
    service: EmployeeService = Depends(get_employee_service)
):
    """Список сотрудников в конкретном подразделении"""
    return await service.get_staff_by_department(department_id)


@router.patch("/{dept_id}", response_model=DepartmentRead, status_code=status.HTTP_200_OK, summary="Обновление подразделения")
async def update_department(
    dept_id: int,
    data: DepartmentUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: DepartmentService = Depends(get_dept_service)
):
    return await service.update_department(current_user, dept_id, data)


@router.delete("/{dept_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удаление подразделения")
async def delete_department(
    dept_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: DepartmentService = Depends(get_dept_service)
):
    await service.delete_department(current_user, dept_id)


@router.patch("/{department_id}/head", response_model=DepartmentRead, status_code=status.HTTP_200_OK, summary="Назначить руководителя")
async def update_department_head(
    department_id: int,
    new_head_id: int = Body(..., embed=True, description="ID нового руководителя"),
    current_user: CurrentUser = Depends(get_current_user),
    service: DepartmentService = Depends(get_dept_service)
):
    """
    Назначение руководителя.
    `embed=True` позволяет передавать в JSON: `{"new_head_id": 123}`
    """
    return await service.set_department_head(current_user, department_id, new_head_id)


@router.delete("/{department_id}/head", status_code=status.HTTP_204_NO_CONTENT, summary="Снять руководителя")
async def remove_department_head(
    department_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: DepartmentService = Depends(get_dept_service)
):
    await service.remove_department_head(current_user, department_id)


@router.patch("/{dept_id}/move", response_model=DepartmentRead, status_code=status.HTTP_200_OK, summary="Переместить подразделение")
async def move_department(
    dept_id: int,
    data: DepartmentMove,
    current_user: CurrentUser = Depends(get_current_user),
    service: DepartmentService = Depends(get_dept_service)
):
    return await service.move_department(current_user, dept_id, data.new_parent_id)