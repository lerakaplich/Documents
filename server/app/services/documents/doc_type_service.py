import logging

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from server.app.database.document_models import DocumentType
from server.app.repositories.doc_type_repo import DocTypeRepository
from server.app.schemas.doc.doc_type import DocTypeCreate, DocTypeUpdate
from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.services.common.security_service import SecurityService

logger = logging.getLogger("app.services.doc_type_service")

class DocTypeService:
    def __init__(self, security: SecurityService, repo: DocTypeRepository):
        self.security = security
        self.repo = repo

    def _check_admin(self, user: CurrentUser) -> None:
        """Вспомогательная проверка прав администратора (синхронная)."""
        if not self.security.is_admin(user):
            logger.warning(
                f"Access denied: user_id={user.id} attempted admin operation on document types",
                extra={"event_type": "doc_type_access_denied", "user_id": user.id}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав. Требуются права администратора."
            )

    async def get_all(self):
        """Получить все доступные типы документов"""
        logger.debug("Fetching all document types", extra={"event_type": "doc_type_get_all_start"})
        types_list = await self.repo.get_all()
        logger.debug(
            f"Retrieved {len(types_list)} document types",
            extra={"event_type": "doc_type_get_all_success", "count": len(types_list)}
        )
        return types_list

    async def get_one(self, type_id: int):
        """Получить один тип документа по ID"""
        doc_type = await self.repo.get_by_id(type_id)
        if not doc_type:
            logger.warning(
                f"Document type type_id={type_id} not found",
                extra={"event_type": "doc_type_not_found", "type_id": type_id}
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тип документа не найден."
            )
        return doc_type

    async def create(self, user: CurrentUser, data: DocTypeCreate):
        """Создать новый тип документа"""
        self._check_admin(user)

        try:
            doc_type = await self.repo.add(data)
            await self.repo.db.commit()

            logger.info(
                f"Document type id={doc_type.id} ('{doc_type.name}') created by admin_id={user.id}",
                extra={
                    "event_type": "doc_type_created",
                    "type_id": doc_type.id,
                    "type_name": doc_type.name,
                    "admin_id": user.id
                }
            )
            return doc_type
        except IntegrityError as e:
            await self.repo.db.rollback()
            logger.warning(
                f"Failed to create document type '{data.name}': name already exists",
                extra={"event_type": "doc_type_duplicate_name", "type_name": data.name, "admin_id": user.id}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Тип документа с таким названием уже существует."
            )
        except Exception as e:
            await self.repo.db.rollback()
            logger.exception(
                f"Unexpected error while creating doc type '{data.name}': {e}",
                extra={"event_type": "doc_type_create_error", "admin_id": user.id}
            )
            raise

    async def update(self, user: CurrentUser, type_id: int, data: DocTypeUpdate):
        """Обновить метаданные типа документа"""
        self._check_admin(user)

        doc_type = await self.repo.get_by_id(type_id)
        if not doc_type:
            logger.warning(
                f"Attempted to update non-existent doc_type_id={type_id} by admin_id={user.id}",
                extra={"event_type": "doc_type_not_found", "type_id": type_id, "admin_id": user.id}
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тип документа не найден."
            )

        try:
            updated_type = await self.repo.update(type_id, data)
            await self.repo.db.commit()

            logger.info(
                f"Document type id={type_id} updated by admin_id={user.id}",
                extra={
                    "event_type": "doc_type_updated",
                    "type_id": type_id,
                    "admin_id": user.id
                }
            )
            return updated_type
        except IntegrityError:
            await self.repo.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Тип документа с таким названием уже существует."
            )
        except Exception as e:
            await self.repo.db.rollback()
            logger.exception(
                f"Failed to update doc_type_id={type_id}: {e}",
                extra={"event_type": "doc_type_update_error", "type_id": type_id, "admin_id": user.id}
            )
            raise

    async def delete(self, user: CurrentUser, type_id: int) -> dict[str, str]:
        """Удалить тип документа (если он не используется в документах)"""
        self._check_admin(user)

        doc_type = await self.repo.get_by_id(type_id)
        if not doc_type:
            logger.warning(
                f"Attempted to delete non-existent doc_type_id={type_id} by admin_id={user.id}",
                extra={"event_type": "doc_type_not_found", "type_id": type_id, "admin_id": user.id}
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Тип документа не найден."
            )

        is_used = await self.repo.is_used_in_documents(type_id)
        if is_used:
            logger.warning(
                f"Cannot delete doc_type_id={type_id}: attached to existing documents",
                extra={"event_type": "doc_type_delete_in_use", "type_id": type_id, "admin_id": user.id}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя удалить тип документа, так как к нему привязаны существующие документы."
            )

        try:
            await self.repo.delete(type_id)
            await self.repo.db.commit()

            logger.info(
                f"Document type id={type_id} deleted successfully by admin_id={user.id}",
                extra={"event_type": "doc_type_deleted", "type_id": type_id, "admin_id": user.id}
            )
            return {"message": "Тип успешно удален"}
        except IntegrityError:
            # На случай, если документ был привязан в момент между is_used и delete
            await self.repo.db.rollback()
            logger.warning(
                f"Integrity error on deleting doc_type_id={type_id}: concurrent document attachment",
                extra={"event_type": "doc_type_delete_fk_violation", "type_id": type_id, "admin_id": user.id}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя удалить тип документа, так как к нему привязаны существующие документы."
            )
        except Exception as e:
            await self.repo.db.rollback()
            logger.exception(
                f"Failed to delete doc_type_id={type_id}: {e}",
                extra={"event_type": "doc_type_delete_error", "type_id": type_id, "admin_id": user.id}
            )
            raise