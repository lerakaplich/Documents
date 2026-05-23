from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date, datetime

from server.app.database.models import DocumentRole


# --- СХЕМЫ ДЛЯ УЧАСТНИКОВ ДОКУМЕНТА ---
class DocEmployeeItem(BaseModel):
    employee_id: int
    role: DocumentRole
    is_approved: bool