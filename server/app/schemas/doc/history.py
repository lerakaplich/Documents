# server/app/schemas/document_history_dto.py
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict


class HistoryEventType(str, Enum):
    CREATED = "created"  # Создание
    STATUS_CHANGED = "status_changed"  # Смена статуса (согласован/отклонен)
    REDIRECTED = "redirected"  # Перенаправление
    COMMENTED = "commented"  # Комментарий
    READ = "read"  # Прочтение


class DocumentHistoryItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_type: str  # 'created', 'status_changed', 'redirected', 'comment', 'read', 'approval'
    created_at: datetime

    # Информация о том, кто совершил действие
    employee_id: Optional[int] = None
    employee_full_name: Optional[str] = None

    # Поля контекста (в зависимости от event_type)
    old_status: Optional[str] = None
    new_status: Optional[str] = None

    # Для перенаправлений (redirected)
    target_employee_id: Optional[int] = None
    target_employee_full_name: Optional[str] = None

    # Текстовые примечания, комментарии, резолюции
    comment_text: Optional[str] = None