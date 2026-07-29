import uuid

from fastapi import HTTPException, status, UploadFile
from typing import Optional, List
from server.app.database.document_models import Document, EmployeeDocument, DocumentRole, AppRights, Read, DocDirection
from server.app.repositories.document_repo import DocumentRepository
from server.app.repositories.employee_repo import EmployeesRepository
from server.app.schemas.doc.document_dto import DocumentCreateForm, AdminMetadataUpdate, ProposedNumberResponse
from sqlalchemy import select

from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.services.documents.attachment_service import AttachmentService


class DocumentService:
    def __init__(self, repo: DocumentRepository, emp_repo: EmployeesRepository, attachment_service: AttachmentService):
        self.repo = repo
        self.emp_repo = emp_repo
        self.attachment_service = attachment_service

    async def create(self, payload: DocumentCreateForm, user: CurrentUser) -> Document:
        """Создание документа с привязкой участников и тегов"""
        async with self.repo.db.begin_nested():
            global_msg_id = payload.global_msg_id or str(uuid.uuid4())
            new_doc = Document(
                type_id=payload.type_id,
                direction=payload.direction,
                title=payload.title,
                about=payload.about,
                reg_number=payload.reg_number,
                sequence_number=payload.sequence_number,
                deadline=payload.deadline,
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

        return new_doc

    async def get_by_id(self, doc_id: int, user_id: int, user_rights: AppRights) -> Document:
        """Получение документа с фиксацией прочтения пользователем"""
        document = await self.repo.get_by_id(doc_id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден.")

        # Разграничение прав: если не админ, проверяем участие в документе
        if user_rights not in [AppRights.admin, AppRights.superadmin]:
            relation = await self.repo.get_user_relation(doc_id, user_id)
            if not relation:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ к документу запрещен.")

        # Фиксация прочтения (Reads)
        read_check = await self.repo.db.execute(
            select(Read).where(Read.document_id == doc_id, Read.employee_id == user_id)
        )
        if not read_check.scalar_one_or_none():
            self.repo.db.add(Read(document_id=doc_id, employee_id=user_id))
            await self.repo.db.commit()

        return document

    async def delete(self, doc_id: int) -> None:
        """Полное удаление документа"""
        document = await self.repo.get_by_id(doc_id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден.")
        await self.repo.delete(doc_id)
        await self.repo.db.commit()

    async def admin_update_metadata(self, document_id: int, payload: AdminMetadataUpdate) -> Document:
        """Административное изменение метаданных в обход ограничений бизнес-логики"""
        document = await self.repo.get_by_id(document_id)
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден.")

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
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ошибка обновления: {str(e)}")

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