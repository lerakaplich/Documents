# bot/middlewares/services.py
from typing import Callable, Any, Awaitable
from aiogram import BaseMiddleware, Bot
from aiogram.types import TelegramObject

# Импортируем ваши репозитории и сервисы из FastAPI-приложения
from server.app.repositories.document_repo import DocumentRepository
from server.app.repositories.employee_repo import EmployeesRepository
from server.app.repositories.attachment_repo import AttachmentRepository
from server.app.repositories.org_repo import OrgRepository
from server.app.services.common.notification_service import NotificationService

from server.app.services.documents.document_service import DocumentService
from server.app.services.documents.attachment_service import AttachmentService
from server.app.services.common.security_service import SecurityService
from server.app.services.common.tiff_converter import DocumentProcessor

class ServicesMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        db_docs = data.get("doc_session")
        db_emp = data.get("emp_session")
        bot: Bot = data.get("bot")

        if db_docs and db_emp:
            emp_repo = EmployeesRepository(db_emp)
            org_repo = OrgRepository(db_emp)
            doc_repo = DocumentRepository(db_docs)
            att_repo = AttachmentRepository(db_docs)

            security_svc = SecurityService(
                emp_repo=emp_repo,
                org_repo=org_repo,
                doc_repo=doc_repo
            )

            processor = DocumentProcessor()
            attachment_svc = AttachmentService(att_repo, processor, security_svc)

            notification_svc = NotificationService(
                bot=bot,
                emp_repo=emp_repo,
                doc_repo=doc_repo
            )

            doc_svc = DocumentService(
                repo=doc_repo,
                emp_repo=emp_repo,
                attachment_service=attachment_svc,
                notification_service=notification_svc,
                security=security_svc
            )

            data["document_service"] = doc_svc
            data["attachment_service"] = attachment_svc

        return await handler(event, data)