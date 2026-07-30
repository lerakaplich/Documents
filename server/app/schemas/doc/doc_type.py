from pydantic import BaseModel, ConfigDict
from typing import Optional, Any

class DocTypeBase(BaseModel):
    name: str
    fields: dict[str, bool] = {}
    auto_num: bool = False
    smdo_code_type: Optional[str] = None

class DocTypeRead(DocTypeBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class DocTypeCreate(DocTypeBase):
    pass

class DocTypeUpdate(BaseModel):
    name: Optional[str] = None
    fields: Optional[dict[str, bool]] = None
    auto_num: Optional[bool] = None
    smdo_code_type: Optional[str] = None