from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Union
from datetime import date, datetime

from server.app.database.document_models import DocStatus, DocDirection, TagPriority
from server.app.schemas.doc.doc_employee_dto import DocEmployeeItem, ParticipantItem
from server.app.schemas.doc.tag_dto import TagRead
from server.app.schemas.doc.attachment_dto import DocumentAttachmentRead


class DocumentCreateForm(BaseModel):
    type_id: int
    direction: DocDirection
    title: Optional[str] = None
    about: Optional[str] = None
    reg_number: Optional[str] = None
    sequence_number: Optional[int] = None
    deadline: Optional[date] = None

    # СМДО / Безопасность (Добавлено на основании новых полей БД)
    global_msg_id: Optional[str] = None  # Локальный UUID или UUID пакета СМДО
    parent_document_id: Optional[int] = None
    confident_flag: int = 0  # 0 - открытый, 1 - ДСП
    clearance_id: Optional[int] = None

    sender_id: Optional[int] = None
    executors: list[int] = []  # ID сотрудников
    recipients: list[int] = []  # ID сотрудников
    tag_ids: list[int] = []

    needs_response: bool = False

class DocumentListItem(BaseModel):
    """Усеченная модель для отображения в главной таблице PyQt6"""
    id: int
    is_read: bool = False
    is_archived: bool = False
    has_attachments: bool = False
    is_pinned: bool = False
    reply_id: Optional[int] = None
    sequence_number: Optional[int] = None
    type_name: str = "Без типа"
    title: Optional[str] = None
    reg_number: Optional[str] = None
    status: DocStatus = DocStatus.under_review
    direction: DocDirection
    sent_date: Optional[date] = None
    deadline: Optional[date] = None
    last_comment_text: Optional[str] = None
    tags: list[TagRead] = []
    participants: list[ParticipantItem] = []

    model_config = ConfigDict(from_attributes=True)


class DocumentDetailRead(BaseModel):
    """Полная карточка документа (открытие по двойному клику в UI)"""
    id: int
    status: DocStatus
    type_id: int
    direction: DocDirection
    title: Optional[str] = None
    about: Optional[str] = None

    reg_number: Optional[str] = None
    sequence_number: Optional[int] = None
    sent_date: Optional[date] = None
    deadline: Optional[date] = None

    incoming_number: Optional[str] = None
    incoming_date: Optional[date] = None

    global_msg_id: str
    parent_document_id: Optional[int] = None
    confident_flag: int
    clearance_id: Optional[int] = None
    numcopy: Optional[str] = None

    source_employee_id: Optional[int] = None
    source_organization_id: Optional[int] = None
    source_official_text: Optional[str] = None

    last_comment_text: Optional[str] = None
    created_at: datetime

    # Вложенные списки
    tags: list[TagRead] = []
    employees: list[DocEmployeeItem] = []
    attachments: list[DocumentAttachmentRead] = []  # Заменило старые плоские пути файлов!

    model_config = ConfigDict(from_attributes=True)

class MarkReadRequest(BaseModel):
    """Схема для пакетной фиксации прочтения"""
    document_ids: list[int]


class DocumentPaginationResponse(BaseModel):
    """Ответ для PyQt6 с поддержкой постраничной пагинации"""
    total: int = Field(..., description="Общее количество документов по фильтрам")
    limit: int = Field(..., description="Размер страницы")
    offset: int = Field(..., description="Смещение")
    items: list[DocumentListItem] = Field(..., description="Массив документов текущей страницы")

    model_config = ConfigDict(from_attributes=True)


class AdminMetadataUpdate(BaseModel):
    """DTO для полного администрирования метаданных"""
    title: Optional[str] = None
    about: Optional[str] = None
    reg_number: Optional[str] = None
    sequence_number: Optional[int] = None
    sent_date: Optional[date] = None
    deadline: Optional[date] = None
    status: Optional[DocStatus] = None
    type_id: Optional[int] = None
    direction: Optional[DocDirection] = None

    model_config = ConfigDict(from_attributes=True)


class ReviewDocumentPayload(BaseModel):
    """Согласование / Отклонение документа на этапе under_review"""
    approved: bool = Field(..., description="True - утвердить, False - отклонить")
    comment: Optional[str] = Field(None, description="Комментарий к решению (замечание)")

class ToggleCompletionPayload(BaseModel):
    is_completed: bool

class RedirectHistoryRead(BaseModel):
    id: int
    document_id: int
    from_employee_id: int
    to_employee_id: int
    redirected_at: datetime
    message: Optional[str]

    class Config:
        from_attributes = True # Позволяет создавать схему из ORM-объектов

class BulkDelegateCreate(BaseModel):
    target_ids: list[int] = Field(..., min_length=1, description="Список ID сотрудников для делегирования")
    message: Optional[str] = Field(None, description="Сопроводительное сообщение/поручение")

class ProposedNumberResponse(BaseModel):
    proposed_number: str
    sequence_number: int

class UnansweredDocumentStat(BaseModel):
    document_id: int
    reg_number: Optional[str] = "Б/Н"
    title: Optional[str] = None
    deadline: Optional[date] = None
    assignees: list[str]  # ФИО Получателей (recipient) и Делегатов (delegate)
    delay_info: Union[int, str]  # Число (дней * 50) или строка "Дедлайн не прошел"

    model_config = ConfigDict(from_attributes=True)