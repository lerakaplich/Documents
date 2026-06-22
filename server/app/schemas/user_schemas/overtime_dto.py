from pydantic import BaseModel, ConfigDict
from datetime import date, time
from typing import Optional

class OvertimeBase(BaseModel):
    employee_id: int
    overtime_date: date
    overtime_start: time
    overtime_end: time
    note_text: Optional[str] = None

class OvertimeCreate(OvertimeBase):
    pass

class OvertimeUpdate(BaseModel):
    overtime_date: Optional[date] = None
    overtime_start: Optional[time] = None
    overtime_end: Optional[time] = None
    note_text: Optional[str] = None

class OvertimeRead(OvertimeBase):
    id: int
    model_config = ConfigDict(from_attributes=True)