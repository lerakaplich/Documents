from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from server.app.database.document_models import Tag
from server.app.schemas.doc.tag_dto import TagCreate, TagUpdate

class TagRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self):
        result = await self.db.execute(select(Tag))
        return result.scalars().all()

    async def get_by_id(self, tag_id: int):
        """Получение одного тэга по ID"""
        result = await self.db.execute(select(Tag).where(Tag.id == tag_id))
        return result.scalar_one_or_none()

    async def add(self, data: TagCreate):
        new_tag = Tag(**data.model_dump())
        self.db.add(new_tag)
        await self.db.commit()
        await self.db.refresh(new_tag)
        return new_tag

    async def update(self, tag_id: int, data: TagUpdate):
        """Обновление тэга с исключением unset полей"""
        stmt = (
            update(Tag)
            .where(Tag.id == tag_id)
            .values(**data.model_dump(exclude_unset=True))
            .returning(Tag)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar_one_or_none()

    async def delete(self, tag_id: int):
        """Удаление тэга"""
        result = await self.db.execute(delete(Tag).where(Tag.id == tag_id).returning(Tag.id))
        await self.db.commit()
        return result.scalar_one_or_none()