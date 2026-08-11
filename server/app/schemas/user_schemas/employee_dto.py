from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date
from server.app.database.document_models import AppRights  # Используется в SystemEmployee


class EmployeeBase(BaseModel):
    service_number: str
    last_name: str
    first_name: str
    patronymic: Optional[str] = None
    phone_number: Optional[str] = None
    work_number: Optional[str] = None
    email: Optional[str] = None
    birth_date: Optional[date] = None
    chat_id: Optional[int] = None

class PositionData(BaseModel):
    department_id: int
    position_name: str
    is_leader: bool = False

class PositionCreate(PositionData):
    pass

class EmployeeCreate(EmployeeBase):
    rights: AppRights  # Права в системе (user/admin/superadmin)
    position: PositionCreate  # Данные о должности

class EmployeePositionRead(BaseModel):
    """Должностная позиция сотрудника (Где и кем работает)"""
    id: int
    department_id: int
    position_name: str
    is_leader: bool

    model_config = ConfigDict(from_attributes=True)

class PositionUpdate(PositionData):
    id: Optional[int] = None

class EmployeeRead(EmployeeBase):
    id: int
    positions: list[EmployeePositionRead] = []  # Список всех занимаемых должностей

    model_config = ConfigDict(from_attributes=True)

class EmployeeListRead(BaseModel):
    id: int
    full_name: str           # Соберем на бэкенде: "Иванов И.И."
    position_name: str       # Из employee_positions
    department_name: str     # Из departments
    phone_number: Optional[str]
    rights: str              # user/admin/superadmin из system_employees

    model_config = ConfigDict(from_attributes=True)

class CurrentUser(BaseModel):
    """Текущий сессионный пользователь приложения СЭД"""
    id: int
    service_number: str
    last_name: str
    first_name: str
    patronymic: Optional[str] = None
    rights: AppRights  # Права из локальной таблицы public.system_employees

    model_config = ConfigDict(from_attributes=True)

class EmployeeDetailRead(EmployeeRead):
    rights: str  # user/admin/superadmin
    is_active: bool

class EmployeeProfileUpdate(BaseModel):
    phone_number: Optional[str] = None
    email: Optional[str] = None


class EmployeeFullUpdate(BaseModel):
    # Поля опциональны, чтобы поддерживать PATCH
    service_number: Optional[str] = None
    last_name: Optional[str] = None
    first_name: Optional[str] = None
    patronymic: Optional[str] = None
    phone_number: Optional[str] = None
    work_number: Optional[str] = None
    email: Optional[str] = None
    birth_date: Optional[date] = None

    # Административные поля
    rights: Optional[AppRights] = None
    is_active: Optional[bool] = None

    # Позиции
    positions: list[PositionUpdate] # Список позиций

    model_config = ConfigDict(from_attributes=True)