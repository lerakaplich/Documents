from pydantic import BaseModel, ConfigDict, Field
from datetime import date, time
from typing import Optional, TypeVar, Generic

T = TypeVar("T")

class PageResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

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
    full_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class OvertimeBulkUpdateNote(BaseModel):
    overtime_ids: list[int] = Field(..., description="Список ID записей переработок")
    note: str = Field(..., description="Новый текст описания/заметки")