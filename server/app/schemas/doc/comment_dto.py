from pydantic import BaseModel, ConfigDict
from datetime import datetime

class CommentRead(BaseModel):
    """Схема для отображения истории замечаний в модальном окне PyQt6"""
    id: int
    text: str
    created_at: datetime
    employee_id: int  # ID автора из db_employees
    author_fio: str   # Склеиваем руками на бэкенде при сборке ответа

    model_config = ConfigDict(from_attributes=True)