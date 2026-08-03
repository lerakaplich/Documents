from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.repositories.doc_type_repo import DocTypeRepository
from server.app.schemas.doc.doc_type import DocTypeCreate, DocTypeUpdate
from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.services.common.security_service import SecurityService


class DocTypeService:
    def __init__(self, db: AsyncSession, security: SecurityService, repo: DocTypeRepository):
        self.db = db
        self.security = security
        self.repo = repo

    async def get_all(self):
        return await self.repo.get_all()

    async def get_one(self, type_id: int):
        doc_type = await self.repo.get_by_id(type_id)
        if not doc_type:
            raise HTTPException(status_code=404, detail="Тип документа не найден")
        return doc_type

    async def create(self, user: CurrentUser, data: DocTypeCreate):
        await self.security.is_admin(user)
        return await self.repo.add(data)

    async def update(self, user: CurrentUser, type_id: int, data: DocTypeUpdate):
        await self.security.is_admin(user)
        updated = await self.repo.update(type_id, data)
        if not updated:
            raise HTTPException(status_code=404, detail="Тип документа не найден")
        return updated

    async def delete(self, user: CurrentUser, type_id: int):
        await self.security.is_admin(user)
        # Дополнительно: можно добавить проверку, не используется ли тип в документах
        deleted = await self.repo.delete(type_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Тип документа не найден")
        return {"message": "Тип успешно удален"}