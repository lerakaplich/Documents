import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from server.bot.config import bot_settings
from server.bot.handlers import router
from server.bot.scheduler import setup_scheduler
from server.app.database.session import get_employees_db  # Твой генератор сессий БД

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("bot_main")


# Middleware для автоматической передачи сессии БД в каждый обработчик aiogram
class DbSessionMiddleware:
    async def __call__(self, handler, event, data):
        async with asynccontextmanager(get_employees_db)() as session:
            data["emp_db"] = session  # Передаем ее в аргументы функции-обработчика
            return await handler(event, data)


async def main():
    logger.info("Запуск инфраструктуры Telegram Bot...")

    # 1. Инициализация Bot и Dispatcher
    bot = Bot(token=bot_settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем Middleware и роутер с обработчиками команд
    dp.update.middleware(DbSessionMiddleware())
    dp.include_router(router)

    # 2. Инициализация планировщика APScheduler (утренняя статистика)
    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("Планировщик APScheduler запущен.")

    # 3. Запуск поллинга (прослушивания обновлений от Telegram)
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