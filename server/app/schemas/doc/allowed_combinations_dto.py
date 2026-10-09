from pydantic import BaseModel
from server.app.database.document_models import DocDirection

class DocumentTypeSimpleRead(BaseModel):
    type_id: int
    type_name: str

class DirectionWithTypesRead(BaseModel):
    direction: DocDirection
    code: int
    label: str  # "Внутреннее" / "Внешнее"
    allowed_types: list[DocumentTypeSimpleRead]