from pydantic import BaseModel, ConfigDict, Field

class DepartmentTypeBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Название типа отдела")

class DepartmentTypeCreate(DepartmentTypeBase):
    pass

class DepartmentTypeUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255, description="Новое название типа отдела")

class DepartmentTypeRead(DepartmentTypeBase):
    id: int
    model_config = ConfigDict(from_attributes=True)