from typing import Optional
from pydantic import BaseModel, ConfigDict

class OrganizationBase(BaseModel):
    unp: str
    smdo_code: Optional[str] = None
    name: str
    short_name: Optional[str] = None  # Краткое наименование
    phone_number: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    is_subscriber: bool = True

class OrganizationRead(OrganizationBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(BaseModel):
    smdo_code: Optional[str] = None
    name: Optional[str] = None
    short_name: Optional[str] = None  # Возможность обновить short_name
    phone_number: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    is_subscriber: Optional[bool] = None