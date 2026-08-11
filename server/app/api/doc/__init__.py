from fastapi import APIRouter

# Импортируем роутеры из разбитых файлов
from .documents import router as docs_router
from .workflow import router as workflow_router
from .attachments import router as attachments_router
from .comments import router as comments_router
from .delegation import router as delegation_router

# Создаем единый роутер для всего раздела документов
doc_router = APIRouter(prefix="/documents", tags=["Documents"])

# Подключаем все части
doc_router.include_router(docs_router)
doc_router.include_router(workflow_router)
doc_router.include_router(attachments_router)
doc_router.include_router(comments_router)
doc_router.include_router(delegation_router)