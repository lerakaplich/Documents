from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status

from server.app.database.session import get_employees_db, get_docs_db
from server.app.deps import get_current_user
from server.app.repositories.document_repo import DocumentRepository
from server.app.repositories.employee_repo import EmployeesRepository
from server.app.repositories.org_repo import OrgRepository
from server.app.schemas.user_schemas.employee_dto import EmployeeRead, EmployeeListRead, CurrentUser, \
    EmployeeDetailRead, EmployeeCreate, EmployeeProfileUpdate, EmployeeFullUpdate
from server.app.schemas.user_schemas.org_dto import DepartmentNode
from server.app.services.employees.employee_service import EmployeeService
from server.app.services.employees.org_service import OrgService

router = APIRouter()

def get_org_service(emp_db: AsyncSession = Depends(get_employees_db)) -> OrgService:
    repo = OrgRepository(emp_db)
    return OrgService(repo)

def get_employee_service(
    emp_db: AsyncSession = Depends(get_employees_db),
    doc_db: AsyncSession = Depends(get_docs_db)
) -> EmployeeService:
    emp_repo = EmployeesRepository(emp_db)
    doc_repo = DocumentRepository(doc_db)
    return EmployeeService(emp_repo, doc_repo)

@router.get("/organizations/{org_id}/structure", response_model=List[DepartmentNode])
async def get_org_structure(
    org_id: int,
    service: OrgService = Depends(get_org_service)
):
    """Возвращает дерево подразделений для PyQt6"""
    return await service.get_org_structure(org_id)

@router.get("/departments/{department_id}/staff", response_model=List[EmployeeRead])
async def get_department_staff(
    department_id: int,
    service: EmployeeService = Depends(get_employee_service)
):
    """Список сотрудников в конкретном подразделении"""
    return await service.get_staff_by_department(department_id)

@router.get("/all", response_model=List[EmployeeListRead])
async def get_all_employees(
    page: int = 1,
    limit: int = 20,
    show_fired: bool = False,
    service: EmployeeService = Depends(get_employee_service)
):
    return await service.get_employees_list(page, limit, show_fired)


@router.get("/{emp_id}", response_model=EmployeeDetailRead)
async def get_employee_detail(
        emp_id: int,
        current_user: CurrentUser = Depends(get_current_user),
        service: EmployeeService = Depends(get_employee_service)
):
    # Проверка прав: Админ или Руководитель выше по иерархии
    if not await service.can_view_employee(current_user, emp_id):
        raise HTTPException(
            status_code=403,
            detail="У вас нет прав на просмотр данных этого сотрудника."
        )

    employee = await service.get_full_employee_info(emp_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    return employee

@router.post("/", status_code=status.HTTP_201_CREATED, response_model=EmployeeRead)
async def create_employee(
    data: EmployeeCreate,
    current_user: CurrentUser = Depends(get_current_user), # Берем текущего пользователя
    service: EmployeeService = Depends(get_employee_service)
):
    """
    Создание нового сотрудника.
    Доступно: Админ, Суперадмин, Руководитель (в рамках своей иерархии).
    """
    return await service.create_employee(current_user, data)

@router.patch("/me/profile", response_model=EmployeeRead)
async def update_my_profile(
    data: EmployeeProfileUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: EmployeeService = Depends(get_employee_service)
):
    return await service.update_own_profile(current_user.id, data)

@router.patch("/{employee_id}", response_model=EmployeeFullUpdate)
async def update_employee_by_manager(
    employee_id: int,
    data: EmployeeFullUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: EmployeeService = Depends(get_employee_service)
):
    return await service.update_employee_by_manager(current_user.id, employee_id, data)

@router.patch("/{employee_id}/leadership")
async def toggle_leadership(
    employee_id: int,
    is_leader: bool,
    current_user: CurrentUser = Depends(get_current_user),
    service: EmployeeService = Depends(get_employee_service)
):
    # Метод сервиса, который меняет только поле is_leader
    return await service.set_leadership(current_user.id, employee_id, is_leader)