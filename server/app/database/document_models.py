import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Integer, String, Text, Boolean, Date, DateTime,
    ForeignKey, UniqueConstraint, Enum as SqlEnum, func, text, LargeBinary
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class BaseDocuments(DeclarativeBase):
    pass


# ============================================================================
# ПЕРЕЧИСЛЕНИЯ (ENUMS) СЭД
# ============================================================================

class AppRights(str, enum.Enum):
    user = 'user'
    admin = 'admin'
    superadmin = 'superadmin'


class DocDirection(str, enum.Enum):
    internal = "internal"
    external = "external"

    @property
    def code(self) -> int:
        mapping = {
            DocDirection.internal: 16,
            DocDirection.external: 17,
        }
        return mapping[self]


class DocStatus(str, enum.Enum):
    under_review = 'under_review'
    partially_approved = 'partially_approved'
    approved = 'approved'
    rejected = 'rejected'


class TagPriority(str, enum.Enum):
    normal = 'normal'
    important = 'important'
    urgent = 'urgent'


class DocumentRole(str, enum.Enum):
    sender = 'sender'
    executor = 'executor'
    recipient = 'recipient'
    delegate = 'delegate'


# ============================================================================
# ТАБЛИЦЫ СПРАВОЧНИКОВ И КОНСТРУКТОРОВ
# ============================================================================

class SecurityClearance(BaseDocuments):
    """Справочник государственных грифов доступа"""
    __tablename__ = "security_clearances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clearance_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)


class DocumentType(BaseDocuments):
    """Конструктор типов документов с кастомными метаданными для UI PyQt6"""
    __tablename__ = "types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    fields: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    auto_num: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    smdo_code_type: Mapped[Optional[str]] = mapped_column(String(50))


class Tag(BaseDocuments):
    """Хэштеги с поддержкой цветовой палитры для PyQt6"""
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    priority: Mapped[TagPriority] = mapped_column(
        SqlEnum(TagPriority, name="tag_priority"),
        server_default="normal",
        nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    color: Mapped[str] = mapped_column(String(7), server_default="#808080", nullable=False)

    documents: Mapped[list["Document"]] = relationship(
        secondary="document_tags",
        back_populates="tags"
    )


# ============================================================================
# СВЯЗУЮЩИЕ И ВСПОМОГАТЕЛЬНЫЕ ТАБЛИЦЫ
# ============================================================================

class DocumentTag(BaseDocuments):
    """Связь документов и тегов (Many-to-Many)"""
    __tablename__ = "document_tags"

    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)


class DocumentReceiver(BaseDocuments):
    """Таблица получателей пакетов (Для веерных рассылок и СМДО)"""
    __tablename__ = "document_receivers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)

    # Микросервисные ссылки на db_employees (без FK на уровне БД)
    target_department_id: Mapped[Optional[int]] = mapped_column(Integer)
    target_organization_id: Mapped[Optional[int]] = mapped_column(Integer)

    target_official_text: Mapped[Optional[str]] = mapped_column(Text)
    delivery_status: Mapped[str] = mapped_column(String(50), server_default="pending", nullable=False)

class DocumentArchive(BaseDocuments):
    """Таблица персонального архива пользователей"""
    __tablename__ = "document_archives"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    employee_id: Mapped[int] = mapped_column(
        Integer, nullable=False  # ID сотрудника из db_employees
    )
    archived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint('employee_id', 'document_id', name='unique_user_document_archive'),
    )

class DocumentPin(BaseDocuments):
    """Таблица закрепленных документов"""
    __tablename__ = "document_pins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    employee_id: Mapped[int] = mapped_column(Integer, nullable=False)
    pinned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint('employee_id', 'document_id', name='unique_user_document_pin'),
    )

class DocumentAttachment(BaseDocuments):
    """Выделенная таблица вложений с поддержкой отсоединенной ЭЦП (Хранение в MinIO)"""
    __tablename__ = "document_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer)
    signature_path: Mapped[Optional[str]] = mapped_column(Text)
    signature_data: Mapped[Optional[bytes]] = mapped_column(LargeBinary)  # BYTEA в PostgreSQL
    smdo_reference_id: Mapped[Optional[str]] = mapped_column(String(100))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DocumentStatusHistory(BaseDocuments):
    """История изменений статусов документов для бизнес-мониторинга"""
    __tablename__ = "document_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False
    )
    old_status: Mapped[Optional[DocStatus]] = mapped_column(
        SqlEnum(DocStatus, name="doc_status"),
        nullable=True
    )
    new_status: Mapped[DocStatus] = mapped_column(
        SqlEnum(DocStatus, name="doc_status"),
        nullable=False
    )

    changed_by_employee_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("system_employees.id", ondelete="SET NULL"),
        nullable=True
    )

    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    comment: Mapped[Optional[str]] = mapped_column(Text)

    # Связи (Relationships)
    document: Mapped["Document"] = relationship(back_populates="status_history")
    employee: Mapped[Optional["SystemEmployee"]] = relationship()

# ============================================================================
# ГЛАВНАЯ СУЩНОСТЬ: ДОКУМЕНТ
# ============================================================================

class Document(BaseDocuments):
    """Главная таблица документов"""
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[DocStatus] = mapped_column(
        SqlEnum(DocStatus, name="doc_status"),
        server_default="under_review",
        nullable=False
    )
    needs_response: Mapped[bool] = mapped_column(
        Boolean,
        server_default="false",
        nullable=False
    )

    type_id: Mapped[int] = mapped_column(Integer, ForeignKey("types.id", ondelete="RESTRICT"), nullable=False)
    direction: Mapped[DocDirection] = mapped_column(SqlEnum(DocDirection, name="doc_direction"), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(Text)
    about: Mapped[Optional[str]] = mapped_column(Text)

    # Внутренние / Исходящие реквизиты
    reg_number: Mapped[Optional[str]] = mapped_column(String(100))
    sequence_number: Mapped[Optional[int]] = mapped_column(Integer)
    sent_date: Mapped[Optional[date]] = mapped_column(Date)
    deadline: Mapped[Optional[date]] = mapped_column(Date)

    # Входящие реквизиты (СМДО)
    incoming_number: Mapped[Optional[str]] = mapped_column(String(100))
    incoming_date: Mapped[Optional[date]] = mapped_column(Date)

    # Системные транспортные поля
    global_msg_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    parent_document_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("documents.id", ondelete="SET NULL"))

    # Безопасность
    confident_flag: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    clearance_id: Mapped[Optional[int]] = mapped_column(Integer,
                                                        ForeignKey("security_clearances.id", ondelete="RESTRICT"))
    numcopy: Mapped[Optional[str]] = mapped_column(String(50))

    # МИКРОСЕРВИСНЫЕ ССЫЛКИ НА db_employees (Простые INTEGER без Foreign Key)
    source_employee_id: Mapped[Optional[int]] = mapped_column(Integer)
    source_organization_id: Mapped[Optional[int]] = mapped_column(Integer)
    source_official_text: Mapped[Optional[str]] = mapped_column(Text)

    last_comment_text: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    archives: Mapped[list["DocumentArchive"]] = relationship(
        cascade="all, delete-orphan"
    )

    # Relationships (Внутри этой же БД)
    tags: Mapped[list["Tag"]] = relationship(
        secondary="document_tags",
        back_populates="documents",
        lazy="selectin"
    )
    employees: Mapped[list["EmployeeDocument"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    attachments: Mapped[list["DocumentAttachment"]] = relationship(
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    status_history: Mapped[list["DocumentStatusHistory"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="DocumentStatusHistory.changed_at.asc()"
    )

    type: Mapped["DocumentType"] = relationship("DocumentType", lazy="selectin")


# ============================================================================
# ИСТОРИЯ, СЕССИИ И АВТОРИЗАЦИЯ (РАБОТА С SYSTEM_EMPLOYEES)
# ============================================================================

class RedirectHistory(BaseDocuments):
    """История перенаправлений"""
    __tablename__ = "redirect_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    from_employee_id: Mapped[int] = mapped_column(Integer, nullable=False)  # ID из db_employees
    to_employee_id: Mapped[int] = mapped_column(Integer, nullable=False)  # ID из db_employees
    redirected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text)


class Comment(BaseDocuments):
    """Комментарии к документам"""
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    employee_id: Mapped[int] = mapped_column(Integer, nullable=False)  # ID автора (из db_employees)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Read(BaseDocuments):
    """Отметки о прочтении"""
    __tablename__ = "reads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    employee_id: Mapped[int] = mapped_column(Integer, nullable=False)  # ID кто прочитал (из db_employees)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('employee_id', 'document_id', name='unique_user_document_read'),
    )


class SystemEmployee(BaseDocuments):
    """Локальная таблица авторизации и системных прав внутри СЭД"""
    __tablename__ = "system_employees"

    id: Mapped[int] = mapped_column(Integer,
                                    primary_key=True)  # Напрямую совпадает с ID физического лица из db_employees
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    patronymic: Mapped[Optional[str]] = mapped_column(Text)
    rights: Mapped[AppRights] = mapped_column(
        SqlEnum(AppRights, name="app_rights"),
        server_default="user",
        nullable=False
    )

    sessions: Mapped[list["UserSession"]] = relationship(back_populates="employee", cascade="all, delete-orphan")
    documents: Mapped[list["EmployeeDocument"]] = relationship(back_populates="employee", cascade="all, delete-orphan")


class EmployeeDocument(BaseDocuments):
    """Связующая таблица согласования (Логика СЭД)"""
    __tablename__ = "employee_document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("system_employees.id", ondelete="CASCADE"),
                                             nullable=False)
    role: Mapped[DocumentRole] = mapped_column(SqlEnum(DocumentRole, name="document_role"), nullable=False)

    # Важно: Сделано Опциональным (Optional), чтобы поддерживать NULL (решение не принято)
    is_approved: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    document: Mapped["Document"] = relationship(back_populates="employees")
    employee: Mapped["SystemEmployee"] = relationship(back_populates="documents")

    __table_args__ = (
        UniqueConstraint('document_id', 'employee_id', 'role', name='unique_doc_employee_role'),
    )


class UserSession(BaseDocuments):
    """Сессии пользователей (Refresh токены)"""
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("system_employees.id", ondelete="CASCADE"),
                                             nullable=False)
    refresh_token: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    device_info: Mapped[Optional[str]] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    employee: Mapped["SystemEmployee"] = relationship(back_populates="sessions")