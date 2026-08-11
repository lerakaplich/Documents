from pydantic import BaseModel, ConfigDict

class DepartmentTypeRead(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)