from pydantic import BaseModel, ConfigDict
from typing import Optional
from .department_type import DepartmentTypeRead # Импортируем тип из соседнего файла

class DepartmentBase(BaseModel):
    organization_id: int
    parent_id: Optional[int] = None
    name: str
    number: Optional[int] = None
    phone_number: Optional[str] = None
    hierarchy_path: Optional[str] = None

class DepartmentRead(DepartmentBase):
    id: int
    department_type: Optional[DepartmentTypeRead] = None
    model_config = ConfigDict(from_attributes=True)

class DepartmentCreate(BaseModel):
    organization_id: int
    parent_id: Optional[int] = None
    department_type_id: Optional[int] = None
    name: str
    number: Optional[int] = None
    phone_number: Optional[str] = None

class DepartmentUpdate(BaseModel):
    parent_id: Optional[int] = None
    name: Optional[str] = None
    number: Optional[int] = None
    phone_number: Optional[str] = None

class DepartmentMove(BaseModel):
    new_parent_id: int