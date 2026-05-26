# --- СОТРУДНИКИ ---
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date

from server.app.database.models import AppRights


class EmployeeBase(BaseModel):
    service_number: str
    last_name: str
    first_name: str
    patronymic: Optional[str] = None
    position: Optional[str] = None
    phone_number: Optional[str] = None
    work_number: Optional[str] = None
    email: Optional[str] = None
    birth_date: Optional[date] = None
    chat_id: Optional[int] = None
    department_id: Optional[int] = None
    division_id: Optional[int] = None
    organization_id: Optional[int] = None

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeRead(EmployeeBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class CurrentUser(BaseModel):
    """Объединенная модель текущего авторизованного пользователя для API"""
    id: int
    service_number: str
    last_name: str
    first_name: str
    patronymic: Optional[str] = None
    position: Optional[str] = None
    rights: AppRights

    model_config = ConfigDict(from_attributes=True)
