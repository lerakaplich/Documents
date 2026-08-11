import uuid
from datetime import date

from fastapi import HTTPException, status
from server.app.database.document_models import Document, EmployeeDocument, DocumentRole, Read, DocDirection, \
    DocStatus
from server.app.repositories.document_repo import DocumentRepository
from server.app.repositories.employee_repo import EmployeesRepository
from server.app.schemas.doc.document_dto import DocumentCreateForm, AdminMetadataUpdate, ProposedNumberResponse, \
    UnansweredDocumentStat
from sqlalchemy import select

from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.services.common.notification_service import NotificationService
from server.app.services.common.security_service import SecurityService
from server.app.services.documents.attachment_service import AttachmentService


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
        """Создание документа с привязкой участников и тегов"""
        # Если пытаются указать другого отправителя, требуется роль администратора
        if payload.sender_id and payload.sender_id != user.id:
            if not self.security.is_admin(user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нельзя создавать документ от имени другого сотрудника без прав администратора."
                )

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
                clearance_id=payload.clearance_id
            )
            self.repo.db.add(new_doc)
            await self.repo.db.flush()

            # 2. Определяем отправителя (из payload, иначе fallback на того, кто выполняет запрос)
            sender_id = payload.sender_id or user.id

            # Множество уже добавленных ID сотрудников, чтобы не допускать дублей
            added_employee_ids = set()

            # Добавляем Отправителя (sender)
            self.repo.db.add(
                EmployeeDocument(
                    document_id=new_doc.id,
                    employee_id=sender_id,
                    role=DocumentRole.sender,
                    is_approved=True
                )
            )
            added_employee_ids.add(sender_id)

            # Добавляем Исполнителей (executors)
            for emp_id in payload.executors:
                if emp_id not in added_employee_ids:
                    self.repo.db.add(
                        EmployeeDocument(
                            document_id=new_doc.id,
                            employee_id=emp_id,
                            role=DocumentRole.executor,
                            is_approved=True
                        )
                    )
                    added_employee_ids.add(emp_id)

            # Добавляем Получателей (recipients)
            for emp_id in payload.recipients:
                if emp_id not in added_employee_ids:
                    self.repo.db.add(
                        EmployeeDocument(
                            document_id=new_doc.id,
                            employee_id=emp_id,
                            role=DocumentRole.recipient,
                            is_approved=None
                        )
                    )
                    added_employee_ids.add(emp_id)

            # 3. Привязываем теги через Many-to-Many
            if payload.tag_ids:
                from server.app.database.document_models import DocumentTag
                for tag_id in set(payload.tag_ids):  # set() уберет возможные дубликаты тегов
                    self.repo.db.add(DocumentTag(document_id=new_doc.id, tag_id=tag_id))

            await self.repo.db.commit()

        await self.repo.db.refresh(
            new_doc,
            attribute_names=["tags", "employees", "attachments", "type"]
        )

        # 4. Фоновая отправка уведомления участникам после фиксации в БД
        await self.notifications.notify_document_created(
            doc_id=new_doc.id,
            actor_id=user.id
        )

        return new_doc

    async def get_user(self, doc_id: int, user: CurrentUser) -> Document:
        """Получение документа с фиксацией прочтения пользователем"""
        document = await self.repo.get_by_id(doc_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Документ не найден."
            )

        # Проверка прав через SecurityService
        if not await self.security.can_access_document(user, doc_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Доступ к документу запрещен."
            )

        # Фиксация прочтения (Reads)
        read_check = await self.repo.db.execute(
            select(Read).where(Read.document_id == doc_id, Read.employee_id == user.id)
        )
        if not read_check.scalar_one_or_none():
            self.repo.db.add(Read(document_id=doc_id, employee_id=user.id))
            await self.repo.db.commit()

        return document

    async def delete(self, doc_id: int, user: CurrentUser) -> None:
        """Полное удаление документа (доступно только администраторам)"""
        if not self.security.is_admin(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для удаления документа."
            )

        document = await self.repo.get_by_id(doc_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Документ не найден."
            )

        await self.repo.delete(doc_id)
        await self.repo.db.commit()

    async def admin_update_metadata(
        self,
        document_id: int,
        payload: AdminMetadataUpdate,
        user: CurrentUser
    ) -> Document:
        """Административное изменение метаданных в обход ограничений бизнес-логики"""
        if not self.security.is_admin(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для администрирования метаданных."
            )

        document = await self.repo.get_by_id(document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Документ не найден."
            )

        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            return document

        for key, value in update_data.items():
            setattr(document, key, value)

        try:
            await self.repo.db.commit()
            await self.repo.db.refresh(document)
            return document
        except Exception as e:
            await self.repo.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ошибка обновления: {str(e)}"
            )

    async def generate_proposed_number(
        self,
        type_id: int,
        direction: DocDirection,
        user_id: int
    ) -> ProposedNumberResponse:
        """
        Генерирует регистрационный номер по маске:
        [Высшее подразделение]-[Код направления]-[Отдел]/[Порядковый номер]
        """
        # 1. Проверяем автонумерацию для типа документа
        auto_num_enabled = await self.repo.is_auto_num_enabled(type_id)
        if not auto_num_enabled:
            return ProposedNumberResponse(proposed_number="", sequence_number=0)

        # 2. Получаем коды подразделений из базы кадров через self.emp_repo
        top_dept_code, sub_dept_code = await self.emp_repo.get_department_codes_for_employee(user_id)

        # 3. Получаем следующий порядковый номер типа
        next_seq = await self.repo.get_next_sequence_number(type_id)

        # 4. Код направления (у DocDirection используем .code)
        direction_code = direction.code

        # 5. Сборка маски
        proposed_str = f"{top_dept_code}-{direction_code}-{sub_dept_code}/{next_seq}"

        return ProposedNumberResponse(
            proposed_number=proposed_str,
            sequence_number=next_seq
        )

    async def get_unanswered_stats(self, user: CurrentUser) -> list[UnansweredDocumentStat]:
        """Расчет статистики и пеней по неотвеченным документам (доступно администраторам)"""
        if not self.security.is_admin(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Просмотр статистики доступен только администраторам."
            )

        unanswered_docs = await self.repo.get_unanswered_documents()
        today = date.today()

        stats: list[UnansweredDocumentStat] = []

        for doc in unanswered_docs:
            # 1. Собираем ФИО Получателей (recipient) и Делегатов (delegate)
            assignees_fio = []
            for emp_doc in doc.employees:
                if emp_doc.role in (DocumentRole.recipient, DocumentRole.delegate) and emp_doc.employee:
                    emp = emp_doc.employee
                    fio = f"{emp.last_name} {emp.first_name}"
                    if emp.patronymic:
                        fio += f" {emp.patronymic}"
                    assignees_fio.append(fio.strip())

            # 2. Расчет задержки (количество дней после дедлайна * 50)
            if doc.deadline:
                days_overdue = (today - doc.deadline).days
                if days_overdue > 0:
                    delay_info = days_overdue * 50  # Количество дней просрочки * 50
                else:
                    delay_info = "Дедлайн не прошел"
            else:
                delay_info = "Дедлайн не прошел"

            stats.append(
                UnansweredDocumentStat(
                    document_id=doc.id,
                    reg_number=doc.reg_number or "Б/Н",
                    title=doc.title,
                    deadline=doc.deadline,
                    assignees=assignees_fio,
                    delay_info=delay_info
                )
            )

        return stats

