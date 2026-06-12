from fastapi import FastAPI, Depends
from sqlalchemy.exc import IntegrityError

from server.app.api.auth_router import router as auth_router
from server.app.api.documents import router as doc_router
from server.app.api.org_router import router as org_router
from server.app.api.positions import router as pos_router
from sqlalchemy.ext.asyncio import AsyncSession
from server.app.api.employees import router as employees_router # Импортируй роутер
from server.app.api.errors import global_exception_handler, integrity_exception_handler
from server.app.database.session import get_docs_db, get_employees_db
from server.app.repositories.employee_repo import EmployeesRepository
from server.app.repositories.document_repo import DocumentRepository
from server.app.services.sync_service import SyncService

app = FastAPI(
    title="СЭД Документооборот — Тестовый Сервер",
    version="1.0.0"
)

# Подключаем наш написанный модуль авторизации
app.include_router(auth_router, prefix="/api/v1")
app.include_router(doc_router, prefix="/api/v1")
app.include_router(org_router, prefix="/api/v1")
app.include_router(pos_router, prefix="/api/v1")
app.include_router(employees_router, prefix="/api/v1/employees", tags=["Employees"])
app.add_exception_handler(Exception, global_exception_handler)
app.add_exception_handler(Exception, global_exception_handler)

async def get_sync_service(
    doc_db: AsyncSession = Depends(get_docs_db),
    emp_db: AsyncSession = Depends(get_employees_db)
):
    emp_repo = EmployeesRepository(emp_db)
    doc_repo = DocumentRepository(doc_db)
    return SyncService(emp_repo, doc_repo)

@app.get("/")
async def root():
    return {"status": "working", "message": "Сервер запущен. Перейдите на /docs для тестов."}