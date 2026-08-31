from fastapi import APIRouter, Depends, HTTPException, Query, status

from server.app.deps import (
    get_current_user,
    get_employee_service,
    get_registry_service,
)
from server.app.schemas.org.structure_search import StructureSearchResult
from server.app.schemas.user_schemas.employee_dto import (
    CurrentUser,
    EmployeeCreate,
    EmployeeDetailRead,
    EmployeeFullUpdate,
    EmployeeListRead,
    EmployeeProfileUpdate,
    EmployeeRead,
)
from server.app.services.documents.registry_service import RegistryService
from server.app.services.employees.employee_service import EmployeeService

router = APIRouter(prefix="/employees", tags=["Employees"])


# =============================================================================
# 1. Поиск и списки (Статические пути)
# =============================================================================


@router.get("/all", response_model=list[EmployeeListRead])
async def get_all_employees(
    page: int = 1,
    limit: int = 20,
    show_fired: bool = False,
    service: EmployeeService = Depends(get_employee_service),
):
    return await service.get_employees_list(page, limit, show_fired)


@router.get(
    "/structure/search",
    response_model=list[StructureSearchResult],
    summary="Поиск по оргструктуре (организации, отделы, сотрудники)",
)
async def search_structure(
    q: str = Query(
        ...,
        min_length=2,
        description="Строка поиска (минимум 2 символа)",
        examples=["Бухгалтер"],  # Заменили example на examples
    ),
    service: RegistryService = Depends(get_registry_service),
):
    return await service.search_structure(query_text=q)


# =============================================================================
# 2. Профиль текущего пользователя (/me)
# =============================================================================


@router.get("/me", response_model=EmployeeDetailRead)
async def get_current_user_profile(
    current_user: CurrentUser = Depends(get_current_user),
    service: EmployeeService = Depends(get_employee_service),
):
    """Получение данных профиля текущего вошедшего пользователя."""
    employee_profile = await service.get_my_profile(current_user)

    if not employee_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль пользователя не найден",
        )

    return employee_profile


@router.patch("/me/profile", response_model=EmployeeRead)
async def update_my_profile(
    data: EmployeeProfileUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: EmployeeService = Depends(get_employee_service),
):
    return await service.update_own_profile(current_user.id, data)


# =============================================================================
# 3. Операции с сущностями (Динамические пути с ID)
# =============================================================================


@router.post(
    "/", status_code=status.HTTP_201_CREATED, response_model=EmployeeRead
)
async def create_employee(
    data: EmployeeCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: EmployeeService = Depends(get_employee_service),
):
    """Создание нового сотрудника.

    Доступно: Админ, Суперадмин, Руководитель (в рамках своей иерархии).
    """
    return await service.create_employee(current_user, data)


@router.get("/{emp_id}", response_model=EmployeeDetailRead)
async def get_employee_detail(
    emp_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: EmployeeService = Depends(get_employee_service),
):
    employee = await service.get_full_employee_info(current_user, emp_id)

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Сотрудник не найден"
        )

    return employee


@router.patch("/{employee_id}", response_model=EmployeeDetailRead)
async def update_employee_by_manager(
    employee_id: int,
    data: EmployeeFullUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: EmployeeService = Depends(get_employee_service),
):
    return await service.update_employee_by_manager(
        current_user, employee_id, data
    )


@router.patch("/{employee_id}/positions/{position_id}/toggle-access")
async def toggle_access_leadership(
    position_id: int,
    is_leader: bool,
    current_user: CurrentUser = Depends(get_current_user),
    service: EmployeeService = Depends(get_employee_service),
):
    return await service.set_access_leadership(
        current_user, position_id, is_leader
    )