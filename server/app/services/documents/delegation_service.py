import logging
from typing import Optional

from fastapi import HTTPException, status
from server.app.database.document_models import DocumentRole
from server.app.repositories.document_repo import DocumentRepository
from server.app.schemas.doc.document_dto import RedirectHistoryRead
from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.services.common.notification_service import NotificationService
from server.app.services.common.security_service import SecurityService

logger = logging.getLogger("app.services.delegation_service")

class DelegationService:
    def __init__(
        self,
        repo: DocumentRepository,
        security: SecurityService,
        notification_service: NotificationService
    ):
        self.repo = repo
        self.security = security
        self.notifications = notification_service

    async def _check_permissions(self, doc_id: int, actor: CurrentUser) -> None:
        """Проверка прав: только админ, отправитель или текущий получатель могут управлять делегатами"""
        if self.security.is_admin(actor):
            return

        relation = await self.repo.get_user_relation(doc_id, actor.id)
        allowed_roles = [DocumentRole.sender, DocumentRole.recipient]

        if relation and relation.role in allowed_roles:
            return

        logger.warning(
            f"Access denied: user_id={actor.id} attempted to manage delegates for doc_id={doc_id}",
            extra={
                "event_type": "delegation_access_denied",
                "doc_id": doc_id,
                "actor_id": actor.id,
                "actor_role": getattr(relation, "role", None)
            }
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="У вас нет прав для управления делегатами этого документа."
        )

    async def add_delegate(
        self,
        doc_id: int,
        actor: CurrentUser,
        target_id: int,
        message: Optional[str] = None
    ) -> None:
        """Назначить сотрудника делегатом"""
        await self._check_permissions(doc_id, actor)

        # Нельзя делегировать самому себе
        if actor.id == target_id:
            logger.warning(
                f"User user_id={actor.id} attempted self-delegation on doc_id={doc_id}",
                extra={"event_type": "delegation_self_assignment_failed", "doc_id": doc_id, "actor_id": actor.id}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя назначить делегатом самого себя."
            )

        try:
            # Атомарная вставка делегата в репозитории
            was_inserted = await self.repo.assign_role_to_employee(doc_id, target_id, DocumentRole.delegate)

            if not was_inserted:
                logger.warning(
                    f"Delegation rejected: target_id={target_id} is already a participant of doc_id={doc_id}",
                    extra={"event_type": "delegation_already_exists", "doc_id": doc_id, "target_id": target_id}
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Этот сотрудник уже является участником документа."
                )

            # Фиксируем перенаправление в истории
            await self.repo.add_redirect_history(doc_id, actor.id, target_id, message)
            await self.repo.db.commit()

            logger.info(
                f"Successfully assigned target_id={target_id} as delegate for doc_id={doc_id} by actor_id={actor.id}",
                extra={
                    "event_type": "delegation_granted",
                    "doc_id": doc_id,
                    "actor_id": actor.id,
                    "target_id": target_id,
                    "has_message": bool(message)
                }
            )
        except HTTPException:
            await self.repo.db.rollback()
            raise
        except Exception as e:
            await self.repo.db.rollback()
            logger.exception(
                f"Failed to add delegate target_id={target_id} to doc_id={doc_id}: {e}",
                extra={"event_type": "delegation_add_error", "doc_id": doc_id, "target_id": target_id}
            )
            raise

        # Изолируем отправку уведомления
        try:
            await self.notifications.notify_delegation_changed(
                doc_id=doc_id,
                delegatee_id=target_id,
                is_granted=True,
                message=message
            )
        except Exception as e:
            logger.error(
                f"Failed to send delegation_granted notification for doc_id={doc_id} to user_id={target_id}: {e}",
                extra={"event_type": "delegation_notify_error", "doc_id": doc_id, "target_id": target_id},
                exc_info=True
            )

    async def add_delegates_bulk(
            self,
            doc_id: int,
            actor: CurrentUser,
            target_ids: list[int],
            message: Optional[str] = None
    ) -> list[int]:
        """Массовое назначение сотрудников делегатами"""
        # 1. Проверяем права актора
        await self._check_permissions(doc_id, actor)

        # Убираем дубликаты из входящего списка и проверяем делегирование самому себе
        unique_target_ids = list(set(target_ids))
        if actor.id in unique_target_ids:
            logger.warning(
                f"User user_id={actor.id} attempted self-delegation in bulk request on doc_id={doc_id}",
                extra={"event_type": "delegation_self_assignment_failed", "doc_id": doc_id, "actor_id": actor.id}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя назначить делегатом самого себя."
            )

        try:
            # 2. Атомарная массовая вставка новых делегатов
            added_emp_ids = await self.repo.assign_role_to_employees_bulk(
                doc_id=doc_id,
                emp_ids=unique_target_ids,
                role=DocumentRole.delegate
            )

            if not added_emp_ids:
                logger.warning(
                    f"Bulk delegation rejected: all targets {unique_target_ids} are already participants of doc_id={doc_id}",
                    extra={"event_type": "delegation_all_already_exist", "doc_id": doc_id,
                           "target_ids": unique_target_ids}
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Все указанные сотрудники уже являются участниками документа."
                )

            # 3. Фиксируем историю перенаправлений только для реально добавленных сотрудников
            await self.repo.add_redirect_history_bulk(
                doc_id=doc_id,
                from_id=actor.id,
                to_ids=added_emp_ids,
                message=message
            )
            await self.repo.db.commit()

            logger.info(
                f"Successfully assigned {len(added_emp_ids)} delegates for doc_id={doc_id} by actor_id={actor.id}",
                extra={
                    "event_type": "delegation_granted_bulk",
                    "doc_id": doc_id,
                    "actor_id": actor.id,
                    "added_emp_ids": added_emp_ids,
                    "has_message": bool(message)
                }
            )
        except HTTPException:
            await self.repo.db.rollback()
            raise
        except Exception as e:
            await self.repo.db.rollback()
            logger.exception(
                f"Failed bulk delegation for doc_id={doc_id}: {e}",
                extra={"event_type": "delegation_bulk_add_error", "doc_id": doc_id, "target_ids": unique_target_ids}
            )
            raise

        # 4. Веерная отправка уведомлений (изолированная)
        for target_id in added_emp_ids:
            try:
                await self.notifications.notify_delegation_changed(
                    doc_id=doc_id,
                    delegatee_id=target_id,
                    is_granted=True,
                    message=message
                )
            except Exception as e:
                logger.error(
                    f"Failed to send delegation_granted notification for doc_id={doc_id} to user_id={target_id}: {e}",
                    extra={"event_type": "delegation_notify_error", "doc_id": doc_id, "target_id": target_id},
                    exc_info=True
                )

        return added_emp_ids

    async def remove_delegate(self, doc_id: int, actor: CurrentUser, target_id: int) -> None:
        """Отозвать права делегата"""
        await self._check_permissions(doc_id, actor)

        # Проверяем, что цель действительно имеет роль делегата
        target_relation = await self.repo.get_user_relation(doc_id, target_id)
        if not target_relation or target_relation.role != DocumentRole.delegate:
            logger.warning(
                f"Cannot remove delegate: target_id={target_id} is not a delegate for doc_id={doc_id}",
                extra={"event_type": "delegation_remove_not_a_delegate", "doc_id": doc_id, "target_id": target_id}
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Указанный сотрудник не является делегатом этого документа."
            )

        try:
            await self.repo.remove_employee_from_doc(doc_id, target_id)
            await self.repo.add_redirect_history(doc_id, actor.id, target_id, "Отозван доступ делегата")
            await self.repo.db.commit()

            logger.info(
                f"Revoked delegation for target_id={target_id} on doc_id={doc_id} by actor_id={actor.id}",
                extra={
                    "event_type": "delegation_revoked",
                    "doc_id": doc_id,
                    "actor_id": actor.id,
                    "target_id": target_id
                }
            )
        except Exception as e:
            await self.repo.db.rollback()
            logger.exception(
                f"Failed to revoke delegation for target_id={target_id} on doc_id={doc_id}: {e}",
                extra={"event_type": "delegation_remove_error", "doc_id": doc_id, "target_id": target_id}
            )
            raise

        # Изолируем отправку уведомления
        try:
            await self.notifications.notify_delegation_changed(
                doc_id=doc_id,
                delegatee_id=target_id,
                is_granted=False
            )
        except Exception as e:
            logger.error(
                f"Failed to send delegation_revoked notification for doc_id={doc_id} to user_id={target_id}: {e}",
                extra={"event_type": "delegation_notify_error", "doc_id": doc_id, "target_id": target_id},
                exc_info=True
            )

    async def get_history(self, doc_id: int) -> list[RedirectHistoryRead]:
        """Получить историю перенаправлений/делегирования"""
        logger.debug(
            f"Fetching redirect history for doc_id={doc_id}",
            extra={"event_type": "delegation_get_history_start", "doc_id": doc_id}
        )
        history_records = await self.repo.get_redirect_history(doc_id)
        return [RedirectHistoryRead.model_validate(h) for h in history_records]