from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class DocumentAttachmentRead(BaseModel):
    id: int
    file_name: str
    storage_path: str  # Путь внутри бакета MinIO
    file_size: Optional[int] = None
    signature_path: Optional[str] = None  # Путь к отсоединенной подписи .p7s
    smdo_reference_id: Optional[str] = None
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)