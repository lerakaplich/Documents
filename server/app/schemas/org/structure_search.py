from enum import Enum
from pydantic import BaseModel


class StructureEntityType(str, Enum):
    ORGANIZATION = "organization"
    DEPARTMENT = "department"
    EMPLOYEE = "employee"


class AncestorItem(BaseModel):
    id: int
    name: str
    type: StructureEntityType


class StructureSearchResult(BaseModel):
    id: int
    type: StructureEntityType
    title: str  # ФИО сотрудника или Название отдела/орг
    subtitle: str | None = None  # Должность для сотрудника или доп. инфо
    ancestors: list[AncestorItem] = []  # Цепочка родителей [Организация -> Отдел]