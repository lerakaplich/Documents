from pydantic import BaseModel, ConfigDict
from typing import Optional

class OrganizationBase(BaseModel):
    unp: str
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