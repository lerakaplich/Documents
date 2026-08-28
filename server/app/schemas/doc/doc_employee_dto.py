from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Union

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
    name: str
    role: Optional[Union[DocumentRole, str]] = Field(None, description="Роль участника в документе")

    model_config = ConfigDict(from_attributes=True)

# --- DTO получателей (DocumentReceiver) ---

class DocumentReceiverCreate(BaseModel):
    """Схема создания адресата документа"""
    target_department_id: Optional[int] = Field(None, description="ID отдела-получателя")
    target_organization_id: Optional[int] = Field(None, description="ID сторонней организации")
    target_official_text: Optional[str] = Field(None, description="Наименование адресата/должности на бланке")


class DocumentReceiverRead(DocumentReceiverCreate):
    """Схема чтения адресата документа"""
    id: int
    document_id: int
    delivery_status: str

    model_config = ConfigDict(from_attributes=True)