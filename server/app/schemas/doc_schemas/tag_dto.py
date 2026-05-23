from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import date, datetime

from server.app.database.models import TagPriority


# --- СХЕМЫ ДЛЯ ХЭШТЕГОВ ---
class TagBase(BaseModel):
    name: str
    priority: TagPriority = TagPriority.normal

class TagRead(TagBase):
    id: int
    model_config = ConfigDict(from_attributes=True)