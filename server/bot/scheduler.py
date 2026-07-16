import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Импортируем твои генераторы сессий (адаптируй пути, если они называются иначе)
from server.app.database.session import get_docs_db, get_employees_db
from server.bot.config import bot_settings
from server.bot.services.tg_client import TelegramClient
from server.bot.services.stats_service import StatsNotificationService

logger = logging.getLogger("bot_scheduler")


async def send_morning_stats_job():
    """Фоновая задача сбора и отправки статистики"""
    logger.info("Запуск ежедневной утренней рассылки статистики...")

    # Так как get_docs_db() и get_employees_db() — это скорее всего асинхронные контекст-менеджеры
    # (или зависимости FastAPI), мы используем их через async with.
    try:
        async with asynccontextmanager(get_employees_db)() as emp_session:
            async with asynccontextmanager(get_docs_db)() as doc_session:
                tg_client = TelegramClient(token=bot_settings.TELEGRAM_BOT_TOKEN)
                service = StatsNotificationService(emp_session, doc_session, tg_client)

                await service.run_daily_broadcast()
                logger.info("Утренняя рассылка успешно завершена.")

    except Exception as e:
        logger.error(f"Критическая ошибка при выполнении рассылки: {e}", exc_info=True)


def setup_scheduler() -> AsyncIOScheduler:
    """Инициализация и настройка планировщика"""
    scheduler = AsyncIOScheduler(timezone=bot_settings.BOT_TIMEZONE)

    scheduler.add_job(
        send_morning_stats_job,
        trigger=CronTrigger(
            hour=bot_settings.STATS_SEND_HOUR,
            minute=bot_settings.STATS_SEND_MINUTE
        ),
        id="daily_morning_stats",
        replace_existing=True
    )

    return scheduler