from pydantic import BaseModel, ConfigDict, Field
from server.app.database.document_models import TagPriority


class TagBase(BaseModel):
    name: str
    priority: TagPriority = TagPriority.normal
    color: str = Field("#808080", max_length=7, description="HEX-код цвета для UI PyQt6")


class TagCreate(TagBase):
    pass


class TagRead(TagBase):
    id: int

    model_config = ConfigDict(from_attributes=True)