from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date, datetime

from server.app.database.document_models import DocumentRole


# --- СХЕМЫ ДЛЯ УЧАСТНИКОВ ДОКУМЕНТА ---
class DocEmployeeItem(BaseModel):
    employee_id: int  # ID из локальной таблицы system_employees
    role: DocumentRole
    is_approved: Optional[bool] = None  # NULL — решение не принято, TRUE — за, FALSE — против
    is_completed: bool = False

    model_config = ConfigDict(from_attributes=True)

class ParticipantItem(BaseModel):
    fio: str
    role: DocumentRole

    model_config = ConfigDict(from_attributes=True)