from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from server.app.database.document_models import TagPriority
from server.app.repositories.tag_repo import TagRepository
from server.app.schemas.doc.tag_dto import TagCreate, TagUpdate
from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.services.security_service import SecurityService


class TagService:
    def __init__(self, db: AsyncSession, security: SecurityService, repo: TagRepository):
        self.db = db
        self.security = security
        self.repo = repo

    async def _check_access(self, user: CurrentUser, priority: TagPriority = None):
        # 1. Проверка на суперадмина для критических приоритетов
        if priority in [TagPriority.important, TagPriority.urgent]:
            await self.security.verify_is_superadmin(user)
            return

        # 2. Если приоритет нормальный — проверяем админа или руководителя
        try:
            await self.security.verify_is_admin(user)
        except HTTPException:
            await self.security.verify_is_leader_at_least_once(user)

    async def get_all(self):
        return await self.repo.get_all()

    async def get_one(self, tag_id: int):
        tag = await self.repo.get_by_id(tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail="Тэг не найден")
        return tag

    async def create(self, user: CurrentUser, data: TagCreate):
        await self._check_access(user, data.priority)
        return await self.repo.add(data)

    async def update(self, user: CurrentUser, tag_id: int, data: TagUpdate):
        # Получаем текущий тэг, чтобы проверить его приоритет (или новый приоритет из данных)
        existing_tag = await self.repo.get_by_id(tag_id)
        if not existing_tag:
            raise HTTPException(status_code=404, detail="Тэг не найден")

        # Проверяем доступ: либо к текущему, либо к новому приоритету
        target_priority = data.priority or existing_tag.priority
        await self._check_access(user, target_priority)

        updated = await self.repo.update(tag_id, data)
        return updated

    async def delete(self, user: CurrentUser, tag_id: int):
        tag = await self.repo.get_by_id(tag_id)
        if not tag:
            raise HTTPException(status_code=404, detail="Тэг не найден")

        await self._check_access(user, tag.priority)
        await self.repo.delete(tag_id)
        return {"message": "Тэг успешно удален"}