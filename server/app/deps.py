from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from server.app.database.document_models import SystemEmployee, AppRights
from server.app.database.session import get_docs_db, get_employees_db  # УБРАЛИ кадровый get_employees_db
from server.app.repositories.comment_repo import CommentRepository
from server.app.repositories.document_repo import DocumentRepository
from server.app.repositories.employee_repo import EmployeesRepository
from server.app.repositories.org_repo import OrgRepository
from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.services.comment_service import CommentService
from server.app.services.documents import DocumentService
from server.app.services.documents.registry_service import DocumentRegistryService
from server.app.services.documents.review_service import DocumentReviewService
from server.app.services.documents.workflow_service import DocumentWorkflowService
from server.app.services.employees.employee_service import EmployeeService
from server.app.services.employees.org_service import OrgService
from server.app.services.security_service import SecurityService

security = HTTPBearer()


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db_docs: AsyncSession = Depends(get_docs_db)
) -> CurrentUser:
    """
    Основная зависимость авторизации СЭД.
    Работает ИСКЛЮЧИТЕЛЬНО с локальной базой db_documents ради микросервисной изоляции.
    """
    token = credentials.credentials

    # Парсинг нашего тестового токена (на проде здесь будет jwt.decode)
    if not token.startswith("access_secret_jwt_for_id_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невалидный сессионный токен.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id_str = token.replace("access_secret_jwt_for_id_", "")
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Искаженный токен авторизации.",
        )

    # Запрашиваем данные пользователя из ЛОКАЛЬНОЙ таблицы system_employees базы СЭД
    sys_result = await db_docs.execute(select(SystemEmployee).where(SystemEmployee.id == user_id))
    system_user = sys_result.scalar_one_or_none()

    if not system_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не зарегистрирован в системе документооборота."
        )

    return CurrentUser(
        id=system_user.id,
        last_name=system_user.last_name,
        first_name=system_user.first_name,
        patronymic=system_user.patronymic,
        rights=system_user.rights,
        service_number="N/A"
    )

def get_security_service(
    emp_db: AsyncSession = Depends(get_employees_db)
) -> SecurityService:
    emp_repo = EmployeesRepository(emp_db)
    org_repo = OrgRepository(emp_db)
    return SecurityService(emp_repo, org_repo)

def get_org_service(
    emp_db: AsyncSession = Depends(get_employees_db),
    security: SecurityService = Depends(get_security_service) # Внедряем сервис прав
) -> OrgService:
    repo = OrgRepository(emp_db)
    return OrgService(repo, security) # Передаем в конструктор OrgService

def get_employee_service(
        emp_db: AsyncSession = Depends(get_employees_db),
        doc_db: AsyncSession = Depends(get_docs_db),
        security: SecurityService = Depends(get_security_service) # Внедряем сервис прав
) -> EmployeeService:
    emp_repo = EmployeesRepository(emp_db)
    doc_repo = DocumentRepository(doc_db)
    org_repo = OrgRepository(emp_db)

    return EmployeeService(emp_repo, doc_repo, org_repo, security)


# --- ФАБРИКИ ЗАВИСИМОСТЕЙ ДЛЯ СЕРВИСОВ ---

def get_doc_service(db_docs: AsyncSession = Depends(get_docs_db)) -> DocumentService:
    repo = DocumentRepository(db_docs)
    return DocumentService(repo)

def get_workflow_service(db_docs: AsyncSession = Depends(get_docs_db)) -> DocumentWorkflowService:
    repo = DocumentRepository(db_docs)
    return DocumentWorkflowService(repo)

def get_review_service(db_docs: AsyncSession = Depends(get_docs_db)) -> DocumentReviewService:
    doc_repo = DocumentRepository(db_docs)
    comment_repo = CommentRepository(db_docs)

    comment_svc = CommentService(comment_repo)

    return DocumentReviewService(db_repo=doc_repo, comment_service=comment_svc)

def get_registry_service(db_docs: AsyncSession = Depends(get_docs_db)) -> DocumentRegistryService:
    repo = DocumentRepository(db_docs)
    return DocumentRegistryService(repo)

def get_comment_service(db_docs: AsyncSession = Depends(get_docs_db)) -> CommentService:
    repo = CommentRepository(db_docs)
    return CommentService(repo)

