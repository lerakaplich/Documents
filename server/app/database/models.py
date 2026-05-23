import enum
from datetime import date, time, datetime
from typing import Optional, List

import jsonb
from sqlalchemy import (
    Integer, String, Text, Boolean, Date, Time, DateTime,
    ForeignKey, ForeignKeyConstraint, UniqueConstraint, Enum, BigInteger, func, text
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

# ============================================================================
# СИСТЕМНЫЕ ПЕРЕЧИСЛЕНИЯ (ENUMS)
# ============================================================================

class AppRights(enum.Enum):
    user = 'user'
    admin = 'admin'
    superadmin = 'superadmin'

class DocDirection(enum.Enum):
    internal = 'внутренние'
    external = 'внешние'

class DocStatus(enum.Enum):
    under_review = 'на рассмотрении'
    partially_approved = 'частично утвержден'
    approved = 'утвержден'
    rejected = 'отклонен'

class TagPriority(enum.Enum):
    normal = 'обычный'
    important = 'важно'
    urgent = 'срочно'

class DocumentRole(enum.Enum):
    sender = 'отправитель'
    executor = 'исполнитель'
    recipient = 'получатель'
    delegate = 'делегат'

# ============================================================================
# МОДЕЛИ КЛАССИЧЕСКОЙ ОРГСТРУКТУРЫ И КАДРОВ
# ============================================================================

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(Text)
    address: Mapped[Optional[str]] = mapped_column(Text)
    site: Mapped[Optional[str]] = mapped_column(Text)
    email: Mapped[Optional[str]] = mapped_column(Text)
    boss: Mapped[Optional[str]] = mapped_column(Text)

class Division(Base):
    __tablename__ = "divisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    boss: Mapped[Optional[str]] = mapped_column(Text)
    phone_number: Mapped[Optional[str]] = mapped_column(Text)
    workshop_code: Mapped[Optional[str]] = mapped_column(Text)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False)

class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    boss: Mapped[Optional[str]] = mapped_column(Text)
    phone_number: Mapped[Optional[str]] = mapped_column(Text)
    division_id: Mapped[int] = mapped_column(Integer, ForeignKey("divisions.id", ondelete="RESTRICT"), nullable=False)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False)

class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    last_name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    patronymic: Mapped[Optional[str]] = mapped_column(Text)
    position: Mapped[Optional[str]] = mapped_column(Text)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20))
    work_number: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(Text)
    birth_date: Mapped[Optional[date]] = mapped_column(Date)
    chat_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    department_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("departments.id", ondelete="SET NULL"))
    division_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("divisions.id", ondelete="SET NULL"))
    organization_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"))

class Overtime(Base):
    __tablename__ = "overtime"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True)
    note_text: Mapped[Optional[str]] = mapped_column(Text)
    overtime_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    overtime_start: Mapped[Optional[time]] = mapped_column(Time)
    overtime_end: Mapped[Optional[time]] = mapped_column(Time)

# ============================================================================
# МОДЕЛИ СЭД И ДОКУМЕНТООБОРОТА
# ============================================================================

class DocumentType(Base):
    __tablename__ = "types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    fields: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))
    auto_num: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[DocStatus] = mapped_column(Enum(DocStatus), server_default="under_review", nullable=False, index=True)
    type_id: Mapped[int] = mapped_column(Integer, ForeignKey("types.id", ondelete="RESTRICT"), nullable=False, index=True)
    direction: Mapped[DocDirection] = mapped_column(Enum(DocDirection), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(Text)
    about: Mapped[Optional[str]] = mapped_column(Text)
    reg_number: Mapped[Optional[str]] = mapped_column(String(100))
    sequence_number: Mapped[Optional[int]] = mapped_column(Integer)
    sent_date: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    deadline: Mapped[Optional[date]] = mapped_column(Date)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    response_file_path: Mapped[Optional[str]] = mapped_column(Text)

class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    priority: Mapped[TagPriority] = mapped_column(Enum(TagPriority), server_default="normal", nullable=False)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

class DocumentTag(Base):
    __tablename__ = "document_tags"

    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)

class RedirectHistory(Base):
    __tablename__ = "redirect_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    from_employee_id: Mapped[int] = mapped_column(Integer, nullable=False)
    to_employee_id: Mapped[int] = mapped_column(Integer, nullable=False)
    redirected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text)

class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class Read(Base):
    __tablename__ = "reads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    employee_id: Mapped[int] = mapped_column(Integer, nullable=False)
    read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint('employee_id', 'document_id', name='unique_user_document_read'),
    )

class SystemEmployee(Base):
    __tablename__ = "system_employees" # Чтобы не путать с таблицей сотрудников из кадров

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rights: Mapped[AppRights] = mapped_column(Enum(AppRights), server_default="user", nullable=False)

class EmployeeDocument(Base):
    __tablename__ = "employee_document"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    employee_id: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[DocumentRole] = mapped_column(Enum(DocumentRole), nullable=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False)

    __table_args__ = (
        UniqueConstraint('document_id', 'employee_id', 'role', name='unique_doc_employee_role'),
    )

class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    refresh_token: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    device_info: Mapped[Optional[str]] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)