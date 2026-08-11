from pydantic import BaseModel, ConfigDict
from typing import Optional

class DocumentReceiverRead(BaseModel):
    id: int
    target_department_id: Optional[int] = None    # Для рассылок внутри МАЗа
    target_organization_id: Optional[int] = None  # Для контрагентов по СМДО
    target_official_text: Optional[str] = None    # Текстовое поле "Кому именно"
    delivery_status: str

    model_config = ConfigDict(from_attributes=True)