from sqlalchemy import insert, select, delete, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.database.document_models import DocumentAttachment, Document


class AttachmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add(self, data: dict):
        stmt = insert(DocumentAttachment).values(**data).returning(DocumentAttachment.id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.scalar()

    async def get_all_by_doc(self, doc_id: int):
        stmt = select(DocumentAttachment).where(DocumentAttachment.document_id == doc_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def delete(self, attach_id: int):
        stmt = delete(DocumentAttachment).where(DocumentAttachment.id == attach_id)
        await self.db.execute(stmt)
        await self.db.commit()

    async def count_by_doc(self, doc_id: int) -> int:
        stmt = select(func.count(DocumentAttachment.id)).where(DocumentAttachment.document_id == doc_id)
        result = await self.db.execute(stmt)
        return result.scalar()

    async def update_archive_path(self, doc_id: int, new_path: str):
        """Обновляет путь к архиву для конкретного документа."""
        stmt = (
            update(DocumentAttachment)
            .where(DocumentAttachment.document_id == doc_id)
            .values(storage_path=new_path)
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def get_document_sent_date(self, doc_id: int):
        """Получает только дату отправки документа для формирования путей."""
        stmt = select(Document.sent_date).where(Document.id == doc_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, attach_id: int):
        """Получает запись вложения по его ID."""
        stmt = select(DocumentAttachment).where(DocumentAttachment.id == attach_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()