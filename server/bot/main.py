import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from server.bot.config import bot_settings
from server.bot.handlers import main_router
from server.bot.middlewares.auth import EmployeeAuthMiddleware
from server.bot.middlewares.db_session import DbSessionMiddleware
from server.bot.middlewares.services import ServicesMiddleware
from server.bot.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("bot_main")




async def main():
    logger.info("Запуск инфраструктуры Telegram Bot...")

    # 1. Инициализация Bot и Dispatcher
    bot = Bot(
        token=bot_settings.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")  # <--- Устанавливаем дефолт здесь!
    )
    dp = Dispatcher(storage=MemoryStorage())

    # 2.1. Создаем и кладем сессии БД в context data
    dp.update.outer_middleware(DbSessionMiddleware())

    # 2.2. Инициализируем сервисы, используя созданные сессии БД
    dp.update.outer_middleware(ServicesMiddleware())

    # 2.3. Авторизуем сотрудника
    dp.update.outer_middleware(EmployeeAuthMiddleware())

    # --- 3. Подключение роутеров ---
    dp.include_router(main_router)

    # 4. Инициализация планировщика APScheduler (утренняя статистика)
    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("Планировщик APScheduler запущен.")

    # 5. Запуск поллинга (прослушивания обновлений от Telegram)
    try:
        logger.info("Бот запущен и слушает новые сообщения...")
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Получен сигнал остановки...")
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logger.info("Бот успешно остановлен.")


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())