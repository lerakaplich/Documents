from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List

from server.app.database.session import get_docs_db
from server.app.database.models import Document, EmployeeDocument, DocumentType, AppRights, DocStatus
from server.app.api.deps import get_current_user, RoleChecker
from server.app.schemas.doc_schemas.doc_employee_dto import DocumentListItem, DocumentCreateForm, DocumentDetailRead, \
    DocumentStatusUpdate
from server.app.schemas.user_schemas.employee_dto import CurrentUser

router = APIRouter(prefix="/documents", tags=["Documents"])


# [C] CREATE: Создание документа (Доступно всем авторизованным)
@router.post("/", response_model=DocumentListItem, status_code=status.HTTP_201_CREATED)
async def create_document(
        payload: DocumentCreateForm,
        current_user: CurrentUser = Depends(get_current_user),
        db_docs: AsyncSession = Depends(get_docs_db)
):
    # 1. Проверяем, существует ли указанный тип документа
    type_check = await db_docs.execute(select(DocumentType).where(DocumentType.id == payload.type_id))
    if not type_check.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Указанный тип документа не существует.")

    # 2. Создаем сам документ (путь к файлу пока имитируем)
    new_doc = Document(
        type_id=payload.type_id,
        direction=payload.direction,
        title=payload.title,
        about=payload.about,
        reg_number=payload.reg_number,
        deadline=payload.deadline,
        file_path=f"storage/docs/{payload.reg_number or 'temp'}.zip"
    )
    db_docs.add(new_doc)
    await db_docs.flush()  # Получаем автоматически сгенерированный id документа

    # 3. Привязываем создателя документа как 'отправителя'
    owner_relation = EmployeeDocument(
        document_id=new_doc.id,
        employee_id=current_user.id,
        role="отправитель",
        is_approved=True
    )
    db_docs.add(owner_relation)

    # 4. Привязываем исполнителей и получателей, которых передал фронтенд
    for emp_id in payload.executors:
        db_docs.add(EmployeeDocument(document_id=new_doc.id, employee_id=emp_id, role="исполнитель", is_approved=True))

    for emp_id in payload.recipients:
        db_docs.add(EmployeeDocument(document_id=new_doc.id, employee_id=emp_id, role="получатель", is_approved=False))

    return new_doc


# [R] READ ALL: Получить список документов (С фильтрацией "Мои документы")
@router.get("/", response_model=List[DocumentListItem])
async def get_documents(
        current_user: CurrentUser = Depends(get_current_user),
        db_docs: AsyncSession = Depends(get_docs_db)
):
    # Если пользователь — админ, он видит ВСЕ документы в системе
    if current_user.role in [AppRights.admin, AppRights.superadmin]:
        result = await db_docs.execute(select(Document).order_by(Document.created_at.desc()))
        return result.scalars().all()

    # Если обычный user — вытаскиваем ТОЛЬКО те документы, где он фигурирует в employee_document
    query = (
        select(Document)
        .join(EmployeeDocument, Document.id == EmployeeDocument.document_id)
        .where(EmployeeDocument.employee_id == current_user.id)
        .order_by(Document.created_at.desc())
        .distinct()
    )
    result = await db_docs.execute(query)
    return result.scalars().all()


# [R] READ ONE: Карточка конкретного документа (С проверкой доступа)
@router.get("/{doc_id}", response_model=DocumentDetailRead)
async def get_document_by_id(
        doc_id: int,
        current_user: CurrentUser = Depends(get_current_user),
        db_docs: AsyncSession = Depends(get_docs_db)
):
    result = await db_docs.execute(select(Document).where(Document.id == doc_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден.")

    # Проверка прав: обычный пользователь не может смотреть чужие документы
    if current_user.role not in [AppRights.admin, AppRights.superadmin]:
        access_check = await db_docs.execute(
            select(EmployeeDocument)
            .where(EmployeeDocument.document_id == doc_id, EmployeeDocument.employee_id == current_user.id)
        )
        if not access_check.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Доступ запрещен. Вы не являетесь участником этого документа.")

    return document


# [U] UPDATE STATUS: Утвердить или Отклонить документ
@router.patch("/{doc_id}/status", response_model=DocumentListItem)
async def update_document_status(
        doc_id: int,
        payload: DocumentStatusUpdate,
        current_user: CurrentUser = Depends(get_current_user),
        db_docs: AsyncSession = Depends(get_docs_db)
):
    # 1. Ищем связь текущего пользователя с этим документом
    rel_result = await db_docs.execute(
        select(EmployeeDocument)
        .where(EmployeeDocument.document_id == doc_id, EmployeeDocument.employee_id == current_user.id)
    )
    relation = rel_result.scalar_one_or_none()

    # Изменять статус (утверждать) могут либо админы, либо назначенные получатели/исполнители документа
    if not relation and current_user.role not in [AppRights.admin, AppRights.superadmin]:
        raise HTTPException(status_code=403, detail="Вы не имеете права изменять статус этого документа.")

    # 2. Обновляем статус в основной таблице документов
    doc_result = await db_docs.execute(select(Document).where(Document.id == doc_id))
    document = doc_result.scalar_one_or_none()

    document.status = payload.status

    # Если текущий пользователь был получателем и нажал "Утвердить" — фиксируем это в связующей таблице
    if relation and payload.status == DocStatus.approved:
        relation.is_approved = True

    return document


# [D] DELETE: Удаление документа (Строго для Admin / Superadmin)
@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
        doc_id: int,
        admin_user: CurrentUser = Depends(RoleChecker([AppRights.admin, AppRights.superadmin])),
        db_docs: AsyncSession = Depends(get_docs_db)
):
    result = await db_docs.execute(select(Document).where(Document.id == doc_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден.")

    await db_docs.execute(delete(Document).where(Document.id == doc_id))
    return None