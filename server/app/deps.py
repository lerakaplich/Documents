import logging
from typing import Optional

from aiogram import Bot
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from server.app.config import TELEGRAM_BOT_TOKEN
from server.app.core.security_tokens import decode_access_token
from server.app.database.document_models import SystemEmployee
from server.app.database.session import get_docs_db, get_employees_db  # УБРАЛИ кадровый get_employees_db
from server.app.repositories.attachment_repo import AttachmentRepository
from server.app.repositories.comment_repo import CommentRepository
from server.app.repositories.doc_type_repo import DocTypeRepository
from server.app.repositories.document_repo import DocumentRepository
from server.app.repositories.employee_repo import EmployeesRepository
from server.app.repositories.org_repo import OrgRepository
from server.app.repositories.overtime_repo import OvertimeRepository
from server.app.repositories.session_repo import SessionRepository
from server.app.repositories.tag_repo import TagRepository
from server.app.schemas.user_schemas.employee_dto import CurrentUser
from server.app.services.authorization.auth_service import AuthService
from server.app.services.common.notification_service import NotificationService
from server.app.services.overtime.overtime_export import OvertimeExportService
from server.app.services.overtime.overtime_import import OvertimeImportService
from server.app.services.common.tiff_converter import DocumentProcessor
from server.app.services.documents.attachment_service import AttachmentService
from server.app.services.documents.comment_service import CommentService
from server.app.services.documents.doc_type_service import DocTypeService
from server.app.services.documents.document_service import DocumentService
from server.app.services.documents.registry_service import RegistryService
from server.app.services.documents.review_service import DocumentReviewService
from server.app.services.documents.delegation_service import DelegationService
from server.app.services.documents.workflow_service import WorkflowService
from server.app.services.employees.employee_service import EmployeeService
from server.app.services.org.department_service import DepartmentService
from server.app.services.org.org_service import OrgService
from server.app.services.overtime.overtime import OvertimeService
from server.app.services.common.security_service import SecurityService
from server.app.services.documents.tag_service import TagService

security = HTTPBearer()
logger = logging.getLogger("app.deps.auth")

# Глобальный синглтон бота (инициализируется при старте)
_bot_instance: Optional[Bot] = None

def get_telegram_bot() -> Optional[Bot]:
    global _bot_instance
    if _bot_instance is None and TELEGRAM_BOT_TOKEN:
        _bot_instance = Bot(token=TELEGRAM_BOT_TOKEN)
    return _bot_instance


def get_notification_service(
    db_docs: AsyncSession = Depends(get_docs_db),
    db_emp: AsyncSession = Depends(get_employees_db),
    bot: Optional[Bot] = Depends(get_telegram_bot)
) -> NotificationService:
    doc_repo = DocumentRepository(db_docs)
    emp_repo = EmployeesRepository(db_emp)
    return NotificationService(bot=bot, emp_repo=emp_repo, doc_repo=doc_repo)


async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db_docs: AsyncSession = Depends(get_docs_db)
) -> CurrentUser:
    """Декодирует реальный JWT-токен и проверяет пользователя в локальной базе документов."""
    token = credentials.credentials

    # 1. Валидация и декодирование JWT через единую утилиту
    payload = decode_access_token(token)

    user_id_str = payload.get("sub")
    if not user_id_str:
        logger.warning(
            "JWT verification failed: Missing 'sub' claim in payload",
            extra={"event_type": "jwt_missing_sub"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный токен: отсутствует sub."
        )

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный токен: sub должен быть числом."
        )

    # 2. Проверяем наличие пользователя в СЭД
    sys_result = await db_docs.execute(select(SystemEmployee).where(SystemEmployee.id == user_id))
    system_user = sys_result.scalar_one_or_none()

    if not system_user:
        logger.warning(
            f"User with id={user_id} found in JWT but missing in SystemEmployee table",
            extra={"event_type": "user_not_registered_in_sed", "employee_id": user_id}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не зарегистрирован в системе документооборота."
        )

    return CurrentUser(
        id=int(system_user.id),
        last_name=system_user.last_name,
        first_name=system_user.first_name,
        patronymic=system_user.patronymic,
        rights=system_user.rights,
        service_number=payload.get("service_number", "N/A")  # Берем из токена, если есть!
    )

def get_auth_service(
    db_emp: AsyncSession = Depends(get_employees_db),
    db_docs: AsyncSession = Depends(get_docs_db)
) -> AuthService:
    session_repo = SessionRepository(db_docs)
    return AuthService(db_emp=db_emp, session_repo=session_repo)


def get_security_service(
        emp_db: AsyncSession = Depends(get_employees_db),
        doc_db: AsyncSession = Depends(get_docs_db)
) -> SecurityService:
    emp_repo = EmployeesRepository(emp_db)
    org_repo = OrgRepository(emp_db)
    doc_repo = DocumentRepository(doc_db)

    return SecurityService(
        emp_repo=emp_repo,
        org_repo=org_repo,
        doc_repo=doc_repo
    )

def get_doc_type_service(
    db: AsyncSession = Depends(get_docs_db),
    security: SecurityService = Depends(get_security_service)
) -> DocTypeService:
    repo = DocTypeRepository(db)
    return DocTypeService(security, repo)

def get_tag_service(
    db: AsyncSession = Depends(get_docs_db),
    security: SecurityService = Depends(get_security_service)
) -> TagService:
    repo = TagRepository(db)
    return TagService(security, repo)

def get_org_service(db: AsyncSession = Depends(get_employees_db), security: SecurityService = Depends(get_security_service)) -> OrgService:
    return OrgService(OrgRepository(db), security)

def get_dept_service(db: AsyncSession = Depends(get_employees_db), security: SecurityService = Depends(get_security_service)) -> DepartmentService:
    return DepartmentService(OrgRepository(db), EmployeesRepository(db), security)

def get_employee_service(
        emp_db: AsyncSession = Depends(get_employees_db),
        doc_db: AsyncSession = Depends(get_docs_db),
        security: SecurityService = Depends(get_security_service) # Внедряем сервис прав
) -> EmployeeService:
    emp_repo = EmployeesRepository(emp_db)
    doc_repo = DocumentRepository(doc_db)
    org_repo = OrgRepository(emp_db)

    return EmployeeService(emp_repo, doc_repo, org_repo, security)

def get_overtime_service(
    emp_db: AsyncSession = Depends(get_employees_db),
    security: SecurityService = Depends(get_security_service)
) -> OvertimeService:
    repo = OvertimeRepository(emp_db)
    return OvertimeService(security, repo)


def get_overtime_import_service(
    db_emp: AsyncSession = Depends(get_employees_db),
    security: SecurityService = Depends(get_security_service),
    notification_svc: NotificationService = Depends(get_notification_service)
) -> OvertimeImportService:
    overtime_repo = OvertimeRepository(db_emp)
    employee_repo = EmployeesRepository(db_emp)

    return OvertimeImportService(
        overtime_repo=overtime_repo,
        employee_repo=employee_repo,
        security=security,
        notification_service=notification_svc
    )

def get_overtime_export_service(
    emp_db: AsyncSession = Depends(get_employees_db),
    security: SecurityService = Depends(get_security_service)
) -> OvertimeExportService:
    overtime_repo = OvertimeRepository(emp_db)
    employee_repo = EmployeesRepository(emp_db)
    return OvertimeExportService(
        overtime_repo=overtime_repo,
        employee_repo=employee_repo,
        security=security
    )

def get_attachment_service(
    db_docs: AsyncSession = Depends(get_docs_db),
    security_svc: SecurityService = Depends(get_security_service)
) -> AttachmentService:
    repo = AttachmentRepository(db_docs)
    processor = DocumentProcessor()
    return AttachmentService(repo, processor, security_svc)


# --- ФАБРИКИ ЗАВИСИМОСТЕЙ ДЛЯ СЕРВИСОВ ---

async def get_doc_service(
    db_docs: AsyncSession = Depends(get_docs_db),
    db_emp: AsyncSession = Depends(get_employees_db),
    attachment_svc: AttachmentService = Depends(get_attachment_service),
    notification_svc: NotificationService = Depends(get_notification_service),
    security: SecurityService = Depends(get_security_service)
) -> DocumentService:
    doc_repo = DocumentRepository(db_docs)
    emp_repo = EmployeesRepository(db_emp)

    return DocumentService(
        repo=doc_repo,
        emp_repo=emp_repo,
        attachment_service=attachment_svc,
        notification_service=notification_svc,
        security=security
    )


def get_delegation_service(
    db_docs: AsyncSession = Depends(get_docs_db),
    security: SecurityService = Depends(get_security_service),
    notification_svc: NotificationService = Depends(get_notification_service)
) -> DelegationService:
    doc_repo = DocumentRepository(db_docs)
    return DelegationService(
        repo=doc_repo,
        security=security,
        notification_service=notification_svc
    )

def get_workflow_service(
    db_docs: AsyncSession = Depends(get_docs_db),
) -> WorkflowService:
    repo = DocumentRepository(db_docs)
    return WorkflowService(repo)


def get_review_service(
        db_docs: AsyncSession = Depends(get_docs_db),
        security: SecurityService = Depends(get_security_service),
        notification_svc: NotificationService = Depends(get_notification_service)
) -> DocumentReviewService:
    doc_repo = DocumentRepository(db_docs)
    comment_repo = CommentRepository(db_docs)

    comment_svc = CommentService(repo=comment_repo, notification_service=notification_svc)

    return DocumentReviewService(
        repo=doc_repo,
        comment_service=comment_svc,
        security=security,
        notification_service=notification_svc
    )

def get_registry_service(db_docs: AsyncSession = Depends(get_docs_db)) -> RegistryService:
    repo = DocumentRepository(db_docs)
    return RegistryService(repo)

def get_comment_service(
    db_docs: AsyncSession = Depends(get_docs_db),
    notification_svc: NotificationService = Depends(get_notification_service)
) -> CommentService:
    repo = CommentRepository(db_docs)
    return CommentService(repo=repo, notification_service=notification_svc)

