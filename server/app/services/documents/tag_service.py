import logging

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from server.app.database.document_models import TagPriority
from server.app.repositories.tag_repo import TagRepository
from server.app.schemas.doc.tag_dto import TagCreate, TagUpdate
from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.services.common.security_service import SecurityService

logger = logging.getLogger(__name__)

class TagService:
    def __init__(self, security: SecurityService, repo: TagRepository):
        self.security = security
        self.repo = repo

    async def _check_access(self, user: CurrentUser, priority: TagPriority = None):
        """Проверка прав доступа к операциям над тегами на основе их приоритета."""
        # 1. Для критических приоритетов (important, urgent) требуется быть суперадмином
        if priority in [TagPriority.important, TagPriority.urgent]:
            if not self.security.is_superadmin(user):
                logger.warning(
                    f"Forbidden access to high-priority tag by user_id={user.id}",
                    extra={
                        "event_type": "tag_access_denied",
                        "user_id": user.id,
                        "priority": priority.value if hasattr(priority, 'value') else str(priority)
                    }
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Для управления тегами со срочным или важным приоритетом требуются права суперадминистратора."
                )
            return

        # 2. Для обычного приоритета проверяем: админ ИЛИ руководитель хотя бы одного подразделения
        is_admin = self.security.is_admin(user)
        is_leader = await self.security.is_leader_anywhere(user)

        if not (is_admin or is_leader):
            logger.warning(
                f"Forbidden tag management attempt by user_id={user.id}",
                extra={"event_type": "tag_access_denied", "user_id": user.id}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Управлять тегами могут только администраторы и руководители подразделений."
            )

    async def get_all(self):
        """Получение списка всех тегов."""
        return await self.repo.get_all()

    async def get_one(self, tag_id: int):
        """Получение конкретного тега по ID."""
        tag = await self.repo.get_by_id(tag_id)
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тег не найден."
            )
        return tag

    async def create(self, user: CurrentUser, data: TagCreate):
        """Создание нового тега."""
        await self._check_access(user, data.priority)

        try:
            new_tag = await self.repo.add(data)
            await self.repo.db.commit()

            logger.info(
                f"Tag created successfully: id={new_tag.id}, name='{new_tag.name}' by user_id={user.id}",
                extra={
                    "event_type": "tag_created",
                    "tag_id": new_tag.id,
                    "tag_name": new_tag.name,
                    "user_id": user.id
                }
            )
            return new_tag
        except Exception as e:
            await self.repo.db.rollback()
            logger.error(f"Error creating tag by user_id={user.id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при создании тега."
            )

    async def update(self, user: CurrentUser, tag_id: int, data: TagUpdate):
        """Обновление существующих параметров тега."""
        existing_tag = await self.repo.get_by_id(tag_id)
        if not existing_tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тег не найден."
            )

        # Важно: проверяем доступ И к текущему приоритету, И к новому (если он передается)
        await self._check_access(user, existing_tag.priority)
        if data.priority and data.priority != existing_tag.priority:
            await self._check_access(user, data.priority)

        try:
            updated = await self.repo.update(tag_id, data)
            await self.repo.db.commit()

            logger.info(
                f"Tag tag_id={tag_id} updated by user_id={user.id}",
                extra={
                    "event_type": "tag_updated",
                    "tag_id": tag_id,
                    "user_id": user.id
                }
            )
            return updated
        except Exception as e:
            await self.repo.db.rollback()
            logger.error(f"Error updating tag_id={tag_id} by user_id={user.id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при обновлении тега."
            )

    async def delete(self, user: CurrentUser, tag_id: int):
        """Удаление тега."""
        tag = await self.repo.get_by_id(tag_id)
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тег не найден."
            )

        await self._check_access(user, tag.priority)

        try:
            await self.repo.delete(tag_id)
            await self.repo.db.commit()

            logger.info(
                f"Tag tag_id={tag_id} deleted by user_id={user.id}",
                extra={
                    "event_type": "tag_deleted",
                    "tag_id": tag_id,
                    "user_id": user.id
                }
            )
            return {"message": "Тег успешно удален."}
        except Exception as e:
            await self.repo.db.rollback()
            logger.error(f"Error deleting tag_id={tag_id} by user_id={user.id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при удалении тега."
            )