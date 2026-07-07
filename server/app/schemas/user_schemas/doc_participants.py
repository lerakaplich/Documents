from pydantic import BaseModel
from typing import List, Optional

class ParticipantDTO(BaseModel):
    employee_id: int
    role: str
    last_name: str
    first_name: str
    patronymic: Optional[str] = None