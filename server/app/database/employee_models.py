import enum
from typing import Optional, List
from datetime import date, time

from sqlalchemy import Integer, String, Text, Boolean, Date, BigInteger, ForeignKey, UniqueConstraint, Time, Enum as SqlEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class BaseEmployees(DeclarativeBase):
    pass


class AssignmentType(str, enum.Enum):
    primary = 'primary'
    part_time = 'part_time'
    acting_director = 'acting_director'


class Organization(BaseEmployees):
    """Справочник организаций (И МАЗ, и внешние контрагенты СМДО)"""
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unp: Mapped[str] = mapped_column(String(9), unique=True, nullable=False)
    smdo_code: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    phone_number: Mapped[Optional[str]] = mapped_column(Text)
    address: Mapped[Optional[str]] = mapped_column(Text)
    email: Mapped[Optional[str]] = mapped_column(Text)
    is_subscriber: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)

    departments: Mapped[List["Department"]] = relationship(back_populates="organization", cascade="all, delete-orphan")


class Department(BaseEmployees):
    """Универсальное дерево подразделений (Иерархическая структура)"""
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(Integer, ForeignKey("organizations.id", ondelete="RESTRICT"),
                                                 nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("departments.id", ondelete="CASCADE"))

    name: Mapped[str] = mapped_column(Text, nullable=False)
    number: Mapped[Optional[int]] = mapped_column(Integer)
    phone_number: Mapped[Optional[str]] = mapped_column(Text)
    hierarchy_path: Mapped[Optional[str]] = mapped_column(String(255), index=True)  # Строка вида '1/4/12'

    organization: Mapped["Organization"] = relationship(back_populates="departments")
    positions: Mapped[List["EmployeePosition"]] = relationship(back_populates="department",
                                                               cascade="all, delete-orphan")


class Employee(BaseEmployees):
    """Физические лица (И сотрудники МАЗа, и внешние персоны для СМДО)"""
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    last_name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    patronymic: Mapped[Optional[str]] = mapped_column(Text)
    phone_number: Mapped[Optional[str]] = mapped_column(String(20))
    work_number: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(Text)
    birth_date: Mapped[Optional[date]] = mapped_column(Date)
    chat_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    positions: Mapped[List["EmployeePosition"]] = relationship(back_populates="employee", cascade="all, delete-orphan")

    overtimes: Mapped[List["Overtime"]] = relationship(back_populates="employee", cascade="all, delete-orphan")


class EmployeePosition(BaseEmployees):
    """Промежуточная таблица должностей (КТО ГДЕ РАБОТАЕТ)"""
    __tablename__ = "employee_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey("departments.id", ondelete="CASCADE"),
                                               nullable=False)
    position_name: Mapped[str] = mapped_column(Text, nullable=False)
    assignment_kind: Mapped[AssignmentType] = mapped_column(
        SqlEnum(AssignmentType, name="assignment_type"),
        server_default="primary",
        nullable=False
    )
    is_leader: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)  # Заменяет boss_id

    employee: Mapped["Employee"] = relationship(back_populates="positions")
    department: Mapped["Department"] = relationship(back_populates="positions")

    __table_args__ = (
        UniqueConstraint('employee_id', 'department_id', 'position_name', name='unique_employee_dept_pos'),
    )

class Overtime(BaseEmployees):
    """Учет переработок и сверхурочного времени сотрудников МАЗа"""
    __tablename__ = "overtime"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[int] = mapped_column(Integer, nullable=False) # Номер распоряжения/приказа
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    note_text: Mapped[Optional[str]] = mapped_column(Text) # Причина, например 'Деплой СЭД'
    overtime_date: Mapped[date] = mapped_column(Date, nullable=False)
    overtime_start: Mapped[Optional[time]] = mapped_column(Time)
    overtime_end: Mapped[Optional[time]] = mapped_column(Time)

    # Обратная связь
    employee: Mapped["Employee"] = relationship(back_populates="overtimes")