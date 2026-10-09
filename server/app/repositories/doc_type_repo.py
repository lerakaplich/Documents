from sqlalchemy import select, update, delete, exists
from sqlalchemy.ext.asyncio import AsyncSession
from server.app.database.document_models import DocumentType, Document, DocumentTypeDirection


class DocTypeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self):
        result = await self.db.execute(select(DocumentType))
        return result.scalars().all()

    async def get_by_id(self, type_id: int):
        result = await self.db.execute(select(DocumentType).where(DocumentType.id == type_id))
        return result.scalar_one_or_none()

    async def add(self, data):
        # Если в data передаются allowed_directions, создаем тип и связи
        dump_data = data.model_dump(exclude={"allowed_directions"})
        new_obj = DocumentType(**dump_data)
        self.db.add(new_obj)
        await self.db.flush()  # чтобы получить new_obj.id

        if hasattr(data, "allowed_directions") and data.allowed_directions:
            for direction in data.allowed_directions:
                self.db.add(DocumentTypeDirection(type_id=new_obj.id, direction=direction))

        await self.db.commit()
        await self.db.refresh(new_obj)
        return new_obj

    async def update(self, type_id: int, data):
        dump_data = data.model_dump(exclude_unset=True, exclude={"allowed_directions"})
        stmt = update(DocumentType).where(DocumentType.id == type_id).values(**dump_data).returning(DocumentType)
        result = await self.db.execute(stmt)

        # Если переданы новые направления, можно пересоздать их
        if hasattr(data, "allowed_directions") and data.allowed_directions is not None:
            await self.db.execute(delete(DocumentTypeDirection).where(DocumentTypeDirection.type_id == type_id))
            for direction in data.allowed_directions:
                self.db.add(DocumentTypeDirection(type_id=type_id, direction=direction))

        await self.db.commit()
        return result.scalar_one_or_none()

    async def delete(self, type_id: int):
        result = await self.db.execute(delete(DocumentType).where(DocumentType.id == type_id).returning(DocumentType.id))
        await self.db.commit()
        return result.scalar_one_or_none()

    async def is_used_in_documents(self, type_id: int) -> bool:
        """Проверяет, привязан ли этот тип хотя бы к одному документу."""
        stmt = select(exists().where(Document.type_id == type_id))
        result = await self.db.execute(stmt)
        return bool(result.scalar())