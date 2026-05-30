from fastapi import HTTPException, status
from typing import Optional
from server.app.database.document_models import Document, EmployeeDocument, DocumentRole, AppRights, Read
from server.app.repositories.document_repo import DocumentRepository
from server.app.schemas.doc_schemas.document_dto import DocumentCreateForm, AdminMetadataUpdate
from sqlalchemy import select


class DocumentService:
    def __init__(self, db_repo: DocumentRepository):
        self.repo = db_repo

    async def create(self, payload: DocumentCreateForm, user_id: int) -> Document:
        """Создание документа с привязкой участников и тегов"""
        # 1. Создаем базовую карточку документа (без file_path, вложения теперь в отдельной таблице)
        new_doc = Document(
            type_id=payload.type_id,
            direction=payload.direction,
            title=payload.title,
            about=payload.about,
            reg_number=payload.reg_number,
            deadline=payload.deadline,
            global_msg_id=payload.global_msg_id,
            parent_document_id=payload.parent_document_id,
            confident_flag=payload.confident_flag,
            clearance_id=payload.clearance_id
        )
        self.repo.db.add(new_doc)
        await self.repo.db.flush()

        # 2. Формируем матрицу участников внутреннего согласования МАЗа
        # Отправитель (Sender) автоматически считается согласовавшим
        self.repo.db.add(
            EmployeeDocument(document_id=new_doc.id, employee_id=user_id, role=DocumentRole.sender, is_approved=True))

        for emp_id in payload.executors:
            self.repo.db.add(EmployeeDocument(document_id=new_doc.id, employee_id=emp_id, role=DocumentRole.executor,
                                              is_approved=True))

        for emp_id in payload.recipients:
            self.repo.db.add(EmployeeDocument(document_id=new_doc.id, employee_id=emp_id, role=DocumentRole.recipient,
                                              is_approved=None))

        # 3. Привязываем теги через Many-to-Many
        if payload.tag_ids:
            from server.app.database.document_models import DocumentTag
            for tag_id in payload.tag_ids:
                self.repo.db.add(DocumentTag(document_id=new_doc.id, tag_id=tag_id))

        await self.repo.db.commit()
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