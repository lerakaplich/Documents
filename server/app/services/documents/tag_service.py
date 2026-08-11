from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from server.app.database.document_models import TagPriority
from server.app.repositories.tag_repo import TagRepository
from server.app.schemas.doc.tag_dto import TagCreate, TagUpdate
from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.services.common.security_service import SecurityService


class TagService:
    def __init__(self, db: AsyncSession, security: SecurityService, repo: TagRepository):
        self.db = db
        self.security = security
        self.repo = repo

    async def _check_access(self, user: CurrentUser, priority: TagPriority = None):
        # 1. Для критических приоритетов (important, urgent) требуется быть суперадмином
        if priority in [TagPriority.important, TagPriority.urgent]:
            if not self.security.is_superadmin(user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Для управления тегами со срочным или важным приоритетом требуются права суперадминистратора."
                )
            return

        # 2. Для обычного приоритета проверяем: админ ИЛИ руководитель хотя бы одного подразделения
        is_admin = self.security.is_admin(user)
        is_leader = await self.security.is_leader_anywhere(user)

        if not (is_admin or is_leader):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Управлять тегами могут только администраторы и руководители подразделений."
            )

    async def get_all(self):
        return await self.repo.get_all()

    async def get_one(self, tag_id: int):
        tag = await self.repo.get_by_id(tag_id)
        if not tag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тег не найден")
        return tag

    async def create(self, user: CurrentUser, data: TagCreate):
        await self._check_access(user, data.priority)
        return await self.repo.add(data)

    async def update(self, user: CurrentUser, tag_id: int, data: TagUpdate):
        # Получаем текущий тег, чтобы проверить его приоритет (или новый приоритет из данных)
        existing_tag = await self.repo.get_by_id(tag_id)
        if not existing_tag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тег не найден")

        # Проверяем доступ: либо к текущему, либо к новому приоритету
        target_priority = data.priority or existing_tag.priority
        await self._check_access(user, target_priority)

        updated = await self.repo.update(tag_id, data)
        return updated

    async def delete(self, user: CurrentUser, tag_id: int):
        tag = await self.repo.get_by_id(tag_id)
        if not tag:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Тег не найден")

        await self._check_access(user, tag.priority)
        await self.repo.delete(tag_id)
        return {"message": "Тег успешно удален"}