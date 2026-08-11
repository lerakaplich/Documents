from aiogram import Router

# Импортируем роутеры из отдельных файлов модулей
from server.bot.handlers.common import router as common_router
from server.bot.handlers.support import router as support_router
# Сюда в будущем добавишь:
# from server.bot.handlers.documents import router as docs_router
from server.bot.handlers.overtimes import router as overtime_router
from server.bot.handlers.document_creation import doc_creation_router

# Создаем один корневой роутер для всего пакета обработчиков
main_router = Router()

# Объединяем их (порядок важен: aiogram проверяет хэндлеры сверху вниз)
main_router.include_routers(
    common_router,
    support_router,
    # docs_router,
    overtime_router,
    doc_creation_router
)