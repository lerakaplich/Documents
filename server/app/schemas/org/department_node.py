from pydantic import BaseModel, ConfigDict
from typing import Optional

class DepartmentNode(BaseModel):
    id: int
    name: str
    type_name: Optional[str] = None
    children: list["DepartmentNode"] = []

    model_config = ConfigDict(from_attributes=True)

DepartmentNode.model_rebuild()