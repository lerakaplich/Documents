from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class DepartmentNode(BaseModel):
    id: int
    name: str
    type_name: Optional[str] = None
    children: List["DepartmentNode"] = []

    model_config = ConfigDict(from_attributes=True)

DepartmentNode.model_rebuild()