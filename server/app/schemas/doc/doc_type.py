from pydantic import BaseModel, ConfigDict
from typing import Optional, Any

class DocTypeBase(BaseModel):
    name: str
    fields: Optional[list[Any]] = []
    auto_num: bool = False
    smdo_code_type: Optional[str] = None

class DocTypeRead(DocTypeBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class DocTypeCreate(DocTypeBase):
    pass

class DocTypeUpdate(BaseModel):
    name: Optional[str] = None
    fields: Optional[list[Any]] = None
    auto_num: Optional[bool] = None
    smdo_code_type: Optional[str] = None