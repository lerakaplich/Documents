from pydantic import BaseModel, ConfigDict
from typing import Optional, List
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

class EmployeeCreate(EmployeeBase):
    pass

class EmployeePositionRead(BaseModel):
    """Должностная позиция сотрудника (Где и кем работает)"""
    id: int
    department_id: int
    position_name: str
    assignment_kind: str
    is_leader: bool

    model_config = ConfigDict(from_attributes=True)

class EmployeeRead(EmployeeBase):
    id: int
    positions: List[EmployeePositionRead] = []  # Список всех занимаемых должностей

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