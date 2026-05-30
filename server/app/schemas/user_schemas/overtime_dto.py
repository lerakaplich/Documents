from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import date, time

class OvertimeBase(BaseModel):
    number: int = Field(..., description="Порядковый номер записи или распоряжения")
    employee_id: int = Field(..., description="ID сотрудника из db_employees")
    note_text: Optional[str] = Field(None, description="Причина переработки (например, деплой, авария)")
    overtime_date: date = Field(..., description="Дата переработки")
    overtime_start: Optional[time] = Field(None, description="Время начала сверхурочной работы")
    overtime_end: Optional[time] = Field(None, description="Время окончания сверхурочной работы")

class OvertimeCreate(OvertimeBase):
    """Схема для создания новой записи о переработке на бэкенде"""
    pass

class OvertimeUpdate(BaseModel):
    """Схема для редактирования существующей записи"""
    number: Optional[int] = None
    note_text: Optional[str] = None
    overtime_date: Optional[date] = None
    overtime_start: Optional[time] = None
    overtime_end: Optional[time] = None

class OvertimeRead(OvertimeBase):
    """Схема для отдачи данных в PyQt6 (включает ID записи)"""
    id: int

    model_config = ConfigDict(from_attributes=True)