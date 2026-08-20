from pydantic import BaseModel, ConfigDict, computed_field
from typing import Optional

from sqlalchemy.orm import relationship

from server.app.database.document_models import DocumentRole


# --- СХЕМЫ ДЛЯ УЧАСТНИКОВ ДОКУМЕНТА ---
class DocEmployeeItem(BaseModel):
    employee_id: int  # ID из локальной таблицы system_employees
    role: DocumentRole
    is_approved: Optional[bool] = None  # NULL — решение не принято, TRUE — за, FALSE — против
    is_completed: bool = False
    fio: Optional[str] = None  # Заполняется в сервисе

    model_config = ConfigDict(from_attributes=True)

class ParticipantItem(BaseModel):
    fio: str
    role: DocumentRole

    model_config = ConfigDict(from_attributes=True)