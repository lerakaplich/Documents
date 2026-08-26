from pydantic import BaseModel, ConfigDict, Field, computed_field
from typing import Optional
from datetime import date
from server.app.database.document_models import AppRights  # Используется в SystemEmployee
from server.app.schemas.org import DepartmentPathItem


class EmployeeBase(BaseModel):
    service_number: str
    last_name: str
    first_name: str
    patronymic: Optional[str] = None
    phone_number: Optional[str] = None
    work_number: Optional[str] = None
    email: Optional[str] = None
    birth_date: Optional[date] = None
    chat_id: Optional[int] = None

    @computed_field
    def full_name(self) -> str:
        """Автоматическая сборка ФИО формата 'Иванов И.И.'"""
        init_f = f"{self.first_name[0]}." if self.first_name else ""
        init_p = f"{self.patronymic[0]}." if self.patronymic else ""
        inits = f"{init_f}{init_p}".strip()
        return f"{self.last_name} {inits}".strip()

class EmployeeShortRead(BaseModel):
    """Компактная модель для dropdown/select списков"""
    id: int
    full_name: str  # "Иванов И.И." или "Иванов Иван Иванович"

    model_config = ConfigDict(from_attributes=True)

class PositionData(BaseModel):
    department_id: int
    position_name: str
    is_leader: bool = False
    start_date: date = Field(default_factory=date.today)  # Дата назначения
    end_date: Optional[date] = None  # Дата окончания (None если текущая)

class PositionCreate(PositionData):
    pass

class EmployeeCreate(EmployeeBase):
    rights: AppRights  # Права в системе (user/admin/superadmin)
    position: PositionCreate  # Данные о должности


class EmployeePositionRead(BaseModel):
    """Должность сотрудника с полной цепочкой подразделений"""
    id: int
    department_id: int
    position_name: str
    is_leader: bool
    start_date: date
    end_date: Optional[date] = None

    department_chain: list[DepartmentPathItem] = Field(default_factory=list)

    @computed_field
    def department_path(self) -> list[str]:
        """Автоматически извлекает названия подразделений из цепочки"""
        return [item.name for item in self.department_chain]

    model_config = ConfigDict(from_attributes=True)

class PositionUpdate(BaseModel):
    id: Optional[int] = None
    department_id: Optional[int] = None
    position_name: Optional[str] = None
    is_leader: Optional[bool] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class EmployeeRead(EmployeeBase):
    id: int
    positions: list[EmployeePositionRead] = []  # Список всех занимаемых должностей

    model_config = ConfigDict(from_attributes=True)

class EmployeeListRead(BaseModel):
    id: int
    full_name: str           # Соберем на бэкенде: "Иванов И.И."
    position_name: str       # Из employee_positions
    department_name: str     # Из departments
    phone_number: Optional[str]
    rights: str              # user/admin/superadmin из system_employees

    model_config = ConfigDict(from_attributes=True)

class CurrentUser(BaseModel):
    """Текущий сессионный пользователь приложения СЭД"""
    id: int
    service_number: str
    last_name: str
    first_name: str
    patronymic: Optional[str] = None
    rights: AppRights  # Права из локальной таблицы public.system_employees

    model_config = ConfigDict(from_attributes=True)

class EmployeeDetailRead(EmployeeRead):
    rights: str  # user/admin/superadmin
    is_active: bool

class EmployeeProfileUpdate(BaseModel):
    phone_number: Optional[str] = None
    email: Optional[str] = None


class EmployeeFullUpdate(BaseModel):
    # Поля опциональны, чтобы поддерживать PATCH
    service_number: Optional[str] = None
    last_name: Optional[str] = None
    first_name: Optional[str] = None
    patronymic: Optional[str] = None
    phone_number: Optional[str] = None
    work_number: Optional[str] = None
    email: Optional[str] = None
    birth_date: Optional[date] = None

    # Административные поля
    rights: Optional[AppRights] = None
    is_active: Optional[bool] = None

    # Позиции
    positions: Optional[list[PositionUpdate]] = None  # Список позиций

    model_config = ConfigDict(from_attributes=True)