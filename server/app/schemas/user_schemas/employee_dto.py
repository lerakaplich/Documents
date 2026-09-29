from pydantic import BaseModel, ConfigDict, Field, computed_field
from typing import Optional
from datetime import date
from server.app.database.document_models import AppRights  # Используется в SystemEmployee
from server.app.schemas.org import DepartmentPathItem


class EmployeeBase(BaseModel):
    service_number: str = Field(..., description="Табельный номер", examples=["10425"])
    last_name: str = Field(..., description="Фамилия", examples=["Иванов"])
    first_name: str = Field(..., description="Имя", examples=["Иван"])
    patronymic: Optional[str] = Field(None, description="Отчество", examples=["Иванович"])
    phone_number: Optional[str] = Field(None, description="Личный телефон", examples=["+375291234567"])
    work_number: Optional[str] = Field(None, description="Рабочий/внутренний номер", examples=["402"])
    email: Optional[str] = Field(None, description="Рабочий Email", examples=["ivanov@company.by"])
    birth_date: Optional[date] = Field(None, description="Дата рождения", examples=["1990-05-15"])
    chat_id: Optional[int] = Field(None, description="Telegram Chat ID", examples=[123456789])

    @computed_field
    def full_name(self) -> str:
        """Безопасная сборка ФИО формата 'Иванов И.И.'"""
        init_f = f"{self.first_name[0]}." if self.first_name else ""
        init_p = f"{self.patronymic[0]}." if self.patronymic else ""
        inits = f"{init_f}{init_p}".strip()
        return f"{self.last_name} {inits}".strip()

class EmployeeShortRead(BaseModel):
    """Компактная модель для dropdown/select списков"""
    id: int = Field(..., examples=[1])
    full_name: str = Field(..., examples=["Иванов И.И."])

    model_config = ConfigDict(from_attributes=True)

class PositionData(BaseModel):
    department_id: int = Field(..., description="ID подразделения", examples=[5])
    position_name: str = Field(..., description="Название должности", examples=["Инженер-программист"])
    is_leader: bool = Field(False, description="Флаг руководителя")
    start_date: date = Field(default_factory=date.today, description="Дата назначения")
    end_date: Optional[date] = Field(None, description="Дата окончания")

class PositionCreate(PositionData):
    pass

class EmployeeCreate(EmployeeBase):
    rights: AppRights
    position: PositionCreate

class EmployeePositionRead(BaseModel):
    """Должность сотрудника с полной цепочкой подразделений"""
    id: int = Field(..., examples=[10])
    department_id: int = Field(..., examples=[5])
    position_name: str = Field(..., examples=["Инженер-программист"])
    is_leader: bool = Field(False)
    start_date: date
    end_date: Optional[date] = None

    department_chain: list[DepartmentPathItem] = Field(default_factory=list)

    @computed_field
    def department_path(self) -> list[str]:
        """Автоматически извлекает названия подразделений из цепочки"""
        return [item.name for item in self.department_chain]

    model_config = ConfigDict(from_attributes=True)

class PositionUpdate(BaseModel):
    id: Optional[int] = Field(None, examples=[10])
    department_id: Optional[int] = Field(None, examples=[5])
    position_name: Optional[str] = Field(None, examples=["Ведущий инженер"])
    is_leader: Optional[bool] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class EmployeeRead(EmployeeBase):
    id: int = Field(..., examples=[1])
    positions: list[EmployeePositionRead] = []

    model_config = ConfigDict(from_attributes=True)

class EmployeeListRead(BaseModel):
    id: int = Field(..., examples=[1])
    full_name: str = Field(..., examples=["Иванов И.И."])
    position_name: str = Field(..., examples=["Инженер-программист"])
    department_name: str = Field(..., examples=["Отдел разработки"])
    phone_number: Optional[str] = Field(None, examples=["+375291234567"])
    rights: str = Field(..., examples=["user"])

    model_config = ConfigDict(from_attributes=True)

class CurrentUser(BaseModel):
    """Текущий сессионный пользователь приложения СЭД"""
    id: int = Field(..., examples=[1])
    service_number: str = Field(..., examples=["10425"])
    last_name: str = Field(..., examples=["Иванов"])
    first_name: str = Field(..., examples=["Иван"])
    patronymic: Optional[str] = Field(None, examples=["Иванович"])
    rights: AppRights

    model_config = ConfigDict(from_attributes=True)

class EmployeeDetailRead(EmployeeRead):
    rights: str = Field(..., examples=["user"])
    is_active: bool = Field(True)

class EmployeeProfileUpdate(BaseModel):
    phone_number: Optional[str] = Field(None, examples=["+375291234567"])
    email: Optional[str] = Field(None, examples=["ivanov@company.by"])

class EmployeeFullUpdate(BaseModel):
    service_number: Optional[str] = None
    last_name: Optional[str] = None
    first_name: Optional[str] = None
    patronymic: Optional[str] = None
    phone_number: Optional[str] = None
    work_number: Optional[str] = None
    email: Optional[str] = None
    birth_date: Optional[date] = None

    rights: Optional[AppRights] = None
    is_active: Optional[bool] = None

    positions: Optional[list[PositionUpdate]] = None

    model_config = ConfigDict(from_attributes=True)