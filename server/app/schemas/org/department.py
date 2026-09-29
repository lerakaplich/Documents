from typing import Optional
from pydantic import BaseModel, ConfigDict, computed_field, Field
from .department_type import DepartmentTypeRead


# --- Базовая схема с общими бизнес-полями ---
class DepartmentBase(BaseModel):
    name: str
    number: Optional[int] = None
    phone_number: Optional[str] = None


# --- Схема руководителя для чтения ---
class DepartmentHeadRead(BaseModel):
    id: int
    first_name: str
    last_name: str
    patronymic: Optional[str] = None

    @computed_field
    @property
    def full_name(self) -> str:
        parts = [self.last_name, self.first_name, self.patronymic]
        return " ".join(p for p in parts if p)

    model_config = ConfigDict(from_attributes=True)


# --- DTO для ЧТЕНИЯ (Response) ---
class DepartmentRead(DepartmentBase):
    id: int
    organization_id: int
    parent_id: Optional[int] = None
    hierarchy_path: Optional[str] = None
    head_employee_id: Optional[int] = None

    department_type: Optional[DepartmentTypeRead] = None
    head: Optional[DepartmentHeadRead] = None

    model_config = ConfigDict(from_attributes=True)


# --- DTO для СОЗДАНИЯ (Request) ---
class DepartmentCreate(DepartmentBase):
    organization_id: int
    parent_id: Optional[int] = None
    department_type_id: Optional[int] = None


# --- DTO для ОБНОВЛЕНИЯ (Request) ---
class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    number: Optional[int] = None
    phone_number: Optional[str] = None
    department_type_id: Optional[int] = None


# --- DTO для ПЕРЕМЕЩЕНИЯ (Request) ---
class DepartmentMove(BaseModel):
    new_parent_id: Optional[int] = None