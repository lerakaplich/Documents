from pydantic import BaseModel, ConfigDict
from typing import Optional

from pydantic import BaseModel, ConfigDict
from typing import List

class DepartmentNode(BaseModel):
    id: int
    name: str
    type_name: Optional[str] = None  # Добавьте эту строку
    children: List["DepartmentNode"] = []

    model_config = ConfigDict(from_attributes=True)

# И обязательно не забудьте обновить model_rebuild после изменения
DepartmentNode.model_rebuild()

# Обязательно вызываем для обработки ссылок на самого себя
DepartmentNode.model_rebuild()

class OrganizationBase(BaseModel):
    unp: str  # Уникальный бизнес-ключ
    smdo_code: Optional[str] = None
    name: str
    phone_number: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    is_subscriber: bool = True

class OrganizationRead(OrganizationBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class OrganizationUpdate(BaseModel):
    smdo_code: Optional[str] = None
    name: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    is_subscriber: Optional[bool] = None

class DepartmentBase(BaseModel):
    organization_id: int
    parent_id: Optional[int] = None  # Ссылка на вышестоящий отдел дерева
    name: str
    number: Optional[int] = None
    phone_number: Optional[str] = None
    hierarchy_path: Optional[str] = None  # Путь дерева '1/4/12'

class DepartmentTypeRead(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)

class DepartmentRead(DepartmentBase):
    id: int
    department_type: Optional[DepartmentTypeRead] = None # Теперь фронт увидит объект типа
    model_config = ConfigDict(from_attributes=True)

# Для создания подразделения
class DepartmentCreate(BaseModel):
    organization_id: int
    parent_id: Optional[int] = None
    department_type_id: Optional[int] = None  # Добавили поле
    name: str
    number: Optional[int] = None
    phone_number: Optional[str] = None

# Для обновления подразделения
class DepartmentUpdate(BaseModel):
    parent_id: Optional[int] = None  # Позволяет переносить отдел в другую ветку
    name: Optional[str] = None
    number: Optional[int] = None
    phone_number: Optional[str] = None