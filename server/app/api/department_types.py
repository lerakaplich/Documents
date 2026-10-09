from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.database.session import get_docs_db
from server.app.deps import get_department_type_service, get_current_user
from server.app.schemas.org import DepartmentTypeRead, DepartmentTypeCreate, DepartmentTypeUpdate
from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.services.org.dep_type_service import DepartmentTypeService

router = APIRouter(prefix="/department-types", tags=["Department Types"])

@router.get("/", response_model=list[DepartmentTypeRead])
async def get_department_types(
    skip: int = 0,
    limit: int = 100,
    service: DepartmentTypeService = Depends(get_department_type_service)
):
    """Получить список всех типов отделов"""
    return await service.list_department_types(skip=skip, limit=limit)


@router.get("/{dept_type_id}", response_model=DepartmentTypeRead)
async def get_department_type_by_id(
    dept_type_id: int,
    service: DepartmentTypeService = Depends(get_department_type_service)
):
    """Получить тип отдела по ID"""
    return await service.get_department_type(dept_type_id)


@router.post("/", response_model=DepartmentTypeRead, status_code=status.HTTP_201_CREATED)
async def create_department_type(
    schema: DepartmentTypeCreate,
    current_user: CurrentUser = Depends(get_current_user),
    service: DepartmentTypeService = Depends(get_department_type_service)
):
    """Создать новый тип отдела"""
    return await service.create_department_type(schema)


@router.put("/{dept_type_id}", response_model=DepartmentTypeRead)
async def update_department_type(
    dept_type_id: int,
    schema: DepartmentTypeUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    service: DepartmentTypeService = Depends(get_department_type_service)
):
    """Обновить тип отдела"""
    return await service.update_department_type(dept_type_id, schema)


@router.delete("/{dept_type_id}", status_code=status.HTTP_200_OK)
async def delete_department_type(
    dept_type_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    service: DepartmentTypeService = Depends(get_department_type_service)
):
    """Удалить тип отдела"""
    return await service.delete_department_type(dept_type_id)