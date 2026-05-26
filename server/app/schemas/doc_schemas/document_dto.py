from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date, datetime

from server.app.database.models import DocStatus, DocDirection
from server.app.schemas.doc_schemas.doc_employee_dto import DocEmployeeItem
from server.app.schemas.doc_schemas.tag_dto import TagRead


# --- СХЕМЫ ДЛЯ ДОКУМЕНТОВ ---
class DocumentCreateForm(BaseModel):
    """Данные, которые PyQt6 присылает вместе с файлом при создании"""
    type_id: int
    direction: DocDirection
    title: Optional[str] = None
    about: Optional[str] = None
    reg_number: Optional[str] = None
    deadline: Optional[date] = None

    # Списки ID сотрудников, которых нужно привязать к документу
    executors: List[int] = []  # Исполнители
    recipients: List[int] = []  # Получатели/Утверждающие
    tag_ids: List[int] = []  # Привязанные хэштеги


class DocumentListItem(BaseModel):
    """Усеченная модель для отображения в главной таблице PyQt6 (чтобы сеть не грузить)"""
    id: int
    title: Optional[str]
    reg_number: Optional[str]
    status: DocStatus
    direction: DocDirection
    created_at: datetime
    deadline: Optional[date]

    model_config = ConfigDict(from_attributes=True)


class DocumentDetailRead(BaseModel):
    """Полная карточка документа со всеми связями"""
    id: int
    title: Optional[str]
    about: Optional[str]
    reg_number: Optional[str]
    sequence_number: Optional[int]
    status: DocStatus
    direction: DocDirection
    created_at: datetime
    deadline: Optional[date]
    file_path: str
    response_file_path: Optional[str] = None

    tags: List[TagRead] = []
    employees: List[DocEmployeeItem] = []

    model_config = ConfigDict(from_attributes=True)


class DocumentStatusUpdate(BaseModel):
    """DTO для смены статуса (Утвердить/Отклонить)"""
    status: DocStatus


class DocumentToggleComplete(BaseModel):
    """DTO для отметки выполнения документа (отправка в архив)"""
    is_completed: bool

class AdminMetadataUpdate(BaseModel):
    title: Optional[str] = Field(None, description="Название документа")
    about: Optional[str] = Field(None, description="Аннотация / Краткое содержание")
    reg_number: Optional[str] = Field(None, description="Регистрационный номер")
    sequence_number: Optional[int] = Field(None, description="Порядковый номер")
    sent_date: Optional[date] = Field(None, description="Дата отправки")
    deadline: Optional[date] = Field(None, description="Срок исполнения")
    status: Optional[DocStatus] = Field(None, description="Принудительное изменение статуса документа")
    type_id: Optional[int] = Field(None, description="Изменение типа документа")
    direction: Optional[DocDirection] = Field(None, description="Изменение направления (internal/external)")

    class Config:
        from_attributes = True

class ReviewDocumentPayload(BaseModel):
    """Схема для согласования/отклонения документа"""
    approved: bool = Field(..., description="True - утвердить, False - отклонить")
    comment: Optional[str] = Field(None, description="Необязательный комментарий к решению")

class ToggleCompletionPayload(BaseModel):
    """Схема для переключения В работе / Архив"""
    is_completed: bool = Field(..., description="Состояние выполнения задачи сотрудником")
