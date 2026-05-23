# --- ПЕРЕРАБОТКИ (OVERTIME) ---
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, time

class OvertimeBase(BaseModel):
    number: int
    employee_id: int
    note_text: Optional[str] = None
    overtime_date: date
    overtime_start: Optional[time] = None
    overtime_end: Optional[time] = None

class OvertimeCreate(OvertimeBase):
    pass

class OvertimeRead(OvertimeBase):
    id: int
    model_config = ConfigDict(from_attributes=True)