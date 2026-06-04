from pydantic import BaseModel, ConfigDict
from typing import Optional

from pydantic import BaseModel, ConfigDict
from typing import List

class DepartmentNode(BaseModel):
    id: int
    name: str
    children: List["DepartmentNode"] = []

    model_config = ConfigDict(from_attributes=True)

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


class DepartmentBase(BaseModel):
    organization_id: int
    parent_id: Optional[int] = None  # Ссылка на вышестоящий отдел дерева
    name: str
    number: Optional[int] = None
    phone_number: Optional[str] = None
    hierarchy_path: Optional[str] = None  # Путь дерева '1/4/12'

class DepartmentRead(DepartmentBase):
    id: int
    model_config = ConfigDict(from_attributes=True)