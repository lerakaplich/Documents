import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation

from server.app.services.tiff.photo_tiff_service import PhotoTiffService
from server.bot.config import bot_settings
from server.bot.handlers import main_router
from server.bot.middlewares.auth import EmployeeAuthMiddleware
from server.bot.middlewares.db_session import DbSessionMiddleware
from server.bot.middlewares.services import ServicesMiddleware
from server.bot.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("bot_main")


def build_dispatcher() -> Dispatcher:
    dp = Dispatcher(
        storage=MemoryStorage(),
        # Апдейты одного пользователя обрабатываются последовательно:
        # без этого альбом из N фото теряет файлы на гонке FSM
        events_isolation=SimpleEventIsolation(),
        photo_service=PhotoTiffService(),  # попадает в workflow_data -> аргумент хендлеров
    )

    dp.update.outer_middleware(DbSessionMiddleware())
    dp.update.outer_middleware(ServicesMiddleware())

    auth = EmployeeAuthMiddleware()
    dp.message.outer_middleware(auth)
    dp.callback_query.outer_middleware(auth)

    dp.include_router(main_router)
    return dp


async def main() -> None:
    bot = Bot(
        token=bot_settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = build_dispatcher()

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Вебхук снят (если был установлен), начинаем polling")

    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("Бот запущен")

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())