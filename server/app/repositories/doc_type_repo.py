from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from server.app.database.document_models import DocumentType

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
        new_obj = DocumentType(**data.model_dump())
        self.db.add(new_obj)
        await self.db.commit()
        await self.db.refresh(new_obj)
        return new_obj

    async def update(self, type_id: int, data):
        stmt = update(DocumentType).where(DocumentType.id == type_id).values(**data.model_dump(exclude_unset=True)).returning(DocumentType)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none()

    async def delete(self, type_id: int):
        result = await self.db.execute(delete(DocumentType).where(DocumentType.id == type_id).returning(DocumentType.id))
        await self.db.commit()
        return result.scalar_one_or_none()