from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field
from server.app.database.document_models import DocDirection


class BotAttachmentDTO(BaseModel):
    file_name: str
    storage_path: str  # Путь к загруженному файлу в MinIO
    file_size: Optional[int] = None


class BotDocumentCreateForm(BaseModel):
    type_id: int
    direction: DocDirection

    # Текстовые реквизиты
    title: Optional[str] = None  # Тема
    about: Optional[str] = None  # Касается / Краткое содержание

    # Номера и даты
    reg_number: Optional[str] = None
    sent_date: Optional[date] = Field(default_factory=date.today)
    deadline: Optional[date] = None

    # Безопасностьчто за пиздец на улице

    confident_flag: int = 0
    clearance_id: Optional[int] = None

    # Участники (ID из базы кадров)
    sender_id: int  # Отправитель (пользователь бота)
    executors: List[int] = []  # Исполнители
    recipients: List[int] = []  # Получатели

    # Дополнительно
    tag_ids: List[int] = []
    attachments: List[BotAttachmentDTO] = []
    parent_document_id: Optional[int] = None