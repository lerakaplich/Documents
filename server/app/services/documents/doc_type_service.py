from fastapi import HTTPException, status
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

    def _check_admin(self, user: CurrentUser):
        """Вспомогательная проверка прав администратора (синхронная)."""
        if not self.security.is_admin(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав. Требуются права администратора"
            )

    async def get_all(self):
        return await self.repo.get_all()

    async def get_one(self, type_id: int):
        doc_type = await self.repo.get_by_id(type_id)
        if not doc_type:
            raise HTTPException(status_code=404, detail="Тип документа не найден")
        return doc_type

    async def create(self, user: CurrentUser, data: DocTypeCreate):
        self._check_admin(user)
        return await self.repo.add(data)

    async def update(self, user: CurrentUser, type_id: int, data: DocTypeUpdate):
        self._check_admin(user)

        # Проверяем существование перед обновлением
        doc_type = await self.repo.get_by_id(type_id)
        if not doc_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тип документа не найден"
            )

        return await self.repo.update(type_id, data)

    async def delete(self, user: CurrentUser, type_id: int):
        self._check_admin(user)

        doc_type = await self.repo.get_by_id(type_id)
        if not doc_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тип документа не найден"
            )

        # Проверка: используется ли этот тип хотя бы в одном документе
        is_used = await self.repo.is_used_in_documents(type_id)
        if is_used:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя удалить тип документа, так как к нему привязаны существующие документы"
            )

        await self.repo.delete(type_id)
        return {"message": "Тип успешно удален"}