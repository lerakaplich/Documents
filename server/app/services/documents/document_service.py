import logging
import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from server.app.database.document_models import Document, EmployeeDocument, DocumentRole, DocDirection, \
    DocStatus, DocumentTag
from server.app.repositories.document_repo import DocumentRepository
from server.app.repositories.employee_repo import EmployeesRepository
from server.app.schemas.doc.document_dto import DocumentCreateForm, AdminMetadataUpdate, ProposedNumberResponse, \
    UnansweredDocumentStat, DocumentDetailRead

from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.services.common.notification_service import NotificationService
from server.app.services.common.security_service import SecurityService
from server.app.services.documents.attachment_service import AttachmentService
from server.app.services.documents.registry_service import _format_fio

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(
        self,
        repo: DocumentRepository,
        emp_repo: EmployeesRepository,
        security: SecurityService,
        attachment_service: AttachmentService,
        notification_service: NotificationService
    ):
        self.repo = repo
        self.emp_repo = emp_repo
        self.security = security
        self.attachment_service = attachment_service
        self.notifications = notification_service

    def _determine_initial_status(self, deadline) -> DocStatus:
        """
        Определяет начальный статус документа.
        Если дедлайн не указан — документ сразу утверждается (approved).
        Если дедлайн задан — отправляется на рассмотрение (under_review).
        """
        if deadline is None:
            return DocStatus.approved
        return DocStatus.under_review

    async def create(self, payload: DocumentCreateForm, user: CurrentUser) -> Document:
        """Создание документа с привязкой участников и тегов (Атомарная операция)"""
        sender_id = payload.sender_id or user.id

        # 1. Проверка прав при создании от чужого имени
        if payload.sender_id and payload.sender_id != user.id:
            if not self.security.is_admin(user):
                logger.warning(
                    f"User user_id={user.id} attempted to create a document on behalf of user_id={payload.sender_id} without admin rights",
                    extra={
                        "event_type": "document_creation_forbidden",
                        "actor_id": user.id,
                        "target_sender_id": payload.sender_id,
                    },
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нельзя создавать документ от имени другого сотрудника без прав администратора.",
                )

        try:
            async with self.repo.db.begin_nested():
                initial_status = self._determine_initial_status(payload.deadline)
                global_msg_id = payload.global_msg_id or str(uuid.uuid4())

                new_doc = Document(
                    type_id=payload.type_id,
                    direction=payload.direction,
                    title=payload.title,
                    about=payload.about,
                    reg_number=payload.reg_number,
                    sequence_number=payload.sequence_number,
                    deadline=payload.deadline,
                    needs_response=payload.needs_response,
                    status=initial_status,
                    global_msg_id=global_msg_id,
                    parent_document_id=payload.parent_document_id,
                    confident_flag=payload.confident_flag,
                    clearance_id=payload.clearance_id,
                )
                self.repo.db.add(new_doc)
                await self.repo.db.flush()

                # Учет добавлений для предотвращения уникальных конфликтов
                added_employee_ids = set()

                # Добавляем Отправителя
                self.repo.db.add(
                    EmployeeDocument(
                        document_id=new_doc.id,
                        employee_id=sender_id,
                        role=DocumentRole.sender,
                        is_approved=True,
                    )
                )
                added_employee_ids.add(sender_id)

                # Добавляем Исполнителей
                for emp_id in payload.executors:
                    if emp_id not in added_employee_ids:
                        self.repo.db.add(
                            EmployeeDocument(
                                document_id=new_doc.id,
                                employee_id=emp_id,
                                role=DocumentRole.executor,
                                is_approved=True,
                            )
                        )
                        added_employee_ids.add(emp_id)

                # Добавляем Получателей
                for emp_id in payload.recipients:
                    if emp_id not in added_employee_ids:
                        self.repo.db.add(
                            EmployeeDocument(
                                document_id=new_doc.id,
                                employee_id=emp_id,
                                role=DocumentRole.recipient,
                                is_approved=None,
                            )
                        )
                        added_employee_ids.add(emp_id)

                # Привязываем теги
                if payload.tag_ids:
                    for tag_id in set(payload.tag_ids):
                        self.repo.db.add(DocumentTag(document_id=new_doc.id, tag_id=tag_id))

                await self.repo.db.flush()

            # Фиксируем внешнюю транзакцию только после успеха всех вложенных шагов
            await self.repo.db.commit()

            logger.info(
                f"Document created successfully: doc_id={new_doc.id}, title='{new_doc.title}' by actor_id={user.id}",
                extra={
                    "event_type": "document_created",
                    "doc_id": new_doc.id,
                    "actor_id": user.id,
                    "participants_count": len(added_employee_ids),
                },
            )

        except SQLAlchemyError as e:
            await self.repo.db.rollback()
            logger.exception(
                f"Failed to create document in DB: {e}",
                extra={"event_type": "document_create_db_error", "actor_id": user.id},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ошибка при создании документа в базе данных.",
            )

        # Обновляем связи для возврата полной сущности
        await self.repo.db.refresh(
            new_doc, attribute_names=["tags", "employees", "attachments", "type"]
        )

        # Отправка уведомления (изолирована от ошибки транзакции)
        try:
            await self.notifications.notify_document_created(
                doc_id=new_doc.id, actor_id=user.id
            )
        except Exception as e:
            logger.error(
                f"Failed to send notifications for created doc_id={new_doc.id}: {e}",
                extra={"event_type": "document_create_notification_error", "doc_id": new_doc.id},
                exc_info=True,
            )

        return new_doc

    async def get_detail(self, doc_id: int, user: CurrentUser) -> DocumentDetailRead:
        """
        Чистое получение полной карточки документа (детализированные участники, вложения, теги).
        Операция строго идемпотентна и НЕ производит запись о прочтении.
        """
        # 1. Проверка прав доступа
        if not await self.security.can_access_document(user, doc_id):
            logger.warning(
                f"Access denied to doc_id={doc_id} for user_id={user.id}",
                extra={"event_type": "document_access_denied", "doc_id": doc_id, "user_id": user.id},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ к документу запрещен.",
            )

        # 2. Запрос агрегированной записи с вычисляемыми статусами пользователя
        row = await self.repo.get_detail_by_id(doc_id, user.id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Документ не найден."
            )

        # Примечание: если дополнительные флаги (is_read, is_archived и т.д.) нужны в Detail Read,
        # убедитесь, что они объявлены в DocumentDetailRead (или используйте схему-обёртку).
        doc, is_read, is_archived, is_pinned, reply_id, has_attachments = row

        # 3. Автоматическая валидация и маппинг через Pydantic from_attributes
        # Pydantic сам затянет doc.tags (в TagRead) и doc.attachments (в DocumentAttachmentRead)
        dto = DocumentDetailRead.model_validate(doc, from_attributes=True)

        # 4. Форматируем ФИО для участников, так как это вычисляемое поле бизнес-логики
        for emp_dto, emp_orm in zip(dto.employees, doc.employees):
            if hasattr(emp_orm, "employee") and emp_orm.employee:
                emp_dto.fio = _format_fio(emp_orm.employee)

        return dto

    async def mark_as_read(self, doc_ids: list[int], user: CurrentUser) -> dict:
        """
        Явная фиксация прочтения одного или списка документов.
        Вызывается отдельным эндпоинтом.
        """
        if not doc_ids:
            return {"status": "ok", "marked_count": 0}

        try:
            processed_ids = await self.repo.mark_as_read_bulk(doc_ids=doc_ids, employee_id=user.id)
            logger.info(
                f"Marked docs as read: count={len(processed_ids)} for user_id={user.id}",
                extra={"event_type": "document_marked_read", "user_id": user.id, "doc_ids": processed_ids},
            )
            return {"status": "ok", "marked_count": len(processed_ids)}
        except Exception as e:
            logger.error(
                f"Failed to record read marks for doc_ids={doc_ids}, user_id={user.id}: {e}",
                extra={"event_type": "document_read_mark_error", "doc_ids": doc_ids, "user_id": user.id},
                exc_info=True,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось обновить статус прочтения документов.",
            )

    async def delete(self, doc_id: int, user: CurrentUser) -> None:
        """Полное удаление документа (доступно только администраторам)"""
        if not self.security.is_admin(user):
            logger.warning(
                f"Non-admin user_id={user.id} attempted to delete doc_id={doc_id}",
                extra={"event_type": "document_delete_forbidden", "doc_id": doc_id, "user_id": user.id},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для удаления документа.",
            )

        document = await self.repo.get_by_id(doc_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден."
            )

        await self.repo.delete(doc_id)
        await self.repo.db.commit()

        logger.info(
            f"Document doc_id={doc_id} permanently deleted by admin_id={user.id}",
            extra={"event_type": "document_deleted", "doc_id": doc_id, "admin_id": user.id},
        )

    async def admin_update_metadata(
        self, document_id: int, payload: AdminMetadataUpdate, user: CurrentUser
    ) -> Document:
        """Административное изменение метаданных"""
        if not self.security.is_admin(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для администрирования метаданных.",
            )

        document = await self.repo.get_by_id(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден."
            )

        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            return document

        for key, value in update_data.items():
            setattr(document, key, value)

        try:
            await self.repo.db.commit()
            await self.repo.db.refresh(document)

            logger.info(
                f"Metadata updated for doc_id={document_id} by admin_id={user.id}. Fields: {list(update_data.keys())}",
                extra={
                    "event_type": "document_metadata_updated",
                    "doc_id": document_id,
                    "admin_id": user.id,
                    "updated_fields": list(update_data.keys()),
                },
            )
            return document
        except Exception as e:
            await self.repo.db.rollback()
            logger.exception(
                f"Failed to update metadata for doc_id={document_id}: {e}",
                extra={"event_type": "document_metadata_update_error", "doc_id": document_id},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ошибка обновления: {str(e)}",
            )

    async def generate_proposed_number(
            self, type_id: int, direction: DocDirection, user_id: int
    ) -> ProposedNumberResponse:
        """Генерация автономера для документа"""
        auto_num_enabled = await self.repo.is_auto_num_enabled(type_id)
        if not auto_num_enabled:
            return ProposedNumberResponse(proposed_number="", sequence_number=0)

        top_dept_code, sub_dept_code = await self.emp_repo.get_department_codes_for_employee(user_id)
        next_seq = await self.repo.get_next_sequence_number(type_id)
        direction_code = direction.code

        proposed_str = f"{top_dept_code}-{direction_code}-{sub_dept_code}/{next_seq}"

        return ProposedNumberResponse(
            proposed_number=proposed_str, sequence_number=next_seq
        )

    async def get_unanswered_stats(self, user: CurrentUser) -> list[UnansweredDocumentStat]:
        """Расчет статистики по просроченным документам"""
        if not self.security.is_admin(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Просмотр статистики доступен только администраторам.",
            )

        unanswered_docs = await self.repo.get_unanswered_documents()
        today = date.today()
        stats: list[UnansweredDocumentStat] = []

        for doc in unanswered_docs:
            assignees_fio = []
            for emp_doc in doc.employees:
                if (
                    emp_doc.role in (DocumentRole.recipient, DocumentRole.delegate)
                    and emp_doc.employee
                ):
                    emp = emp_doc.employee
                    fio = f"{emp.last_name} {emp.first_name}"
                    if emp.patronymic:
                        fio += f" {emp.patronymic}"
                    assignees_fio.append(fio.strip())

            # Вычисление дней задержки
            delay_info = 0
            if doc.deadline:
                days_overdue = (today - doc.deadline).days
                if days_overdue > 0:
                    delay_info = days_overdue * 50

            stats.append(
                UnansweredDocumentStat(
                    document_id=doc.id,
                    reg_number=doc.reg_number or "Б/Н",
                    title=doc.title,
                    deadline=doc.deadline,
                    assignees=assignees_fio,
                    delay_info=delay_info,
                )
            )

        return stats
