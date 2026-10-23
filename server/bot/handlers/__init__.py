from aiogram import Router

from server.bot.handlers.document_creation import doc_creation_router
from server.bot.handlers.menu import router as menu_router
from server.bot.handlers.misc import router as misc_router
from server.bot.handlers.overtimes import router as overtime_router
from server.bot.handlers.photo_to_tiff import router as photo_router
from server.bot.handlers.start import router as start_router
from server.bot.handlers.support import router as support_router

main_router = Router()

# Порядок важен: сначала глобальные команды и меню, затем сценарии
main_router.include_routers(
    start_router,
    menu_router,
    misc_router,
    support_router,
    overtime_router,
    photo_router,
    doc_creation_router,
)