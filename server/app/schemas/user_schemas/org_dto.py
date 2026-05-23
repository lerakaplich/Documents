from pydantic import BaseModel, ConfigDict
from typing import Optional

# --- ОРГСТРУКТУРА ---
class OrganizationBase(BaseModel):
    number: int
    name: str
    phone_number: Optional[str] = None
    address: Optional[str] = None
    site: Optional[str] = None
    email: Optional[str] = None
    boss: Optional[str] = None

class OrganizationRead(OrganizationBase):
    id: int
    model_config = ConfigDict(from_attributes=True)




