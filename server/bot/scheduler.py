import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram.exceptions import TelegramNetworkError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Импортируем твои генераторы сессий (адаптируй пути, если они называются иначе)
from server.app.database.session import get_docs_db, get_employees_db
from server.bot.config import bot_settings
from server.bot.services.tg_client import TelegramClient
from server.bot.services.stats_service import StatsNotificationService

logger = logging.getLogger("bot_scheduler")


async def send_morning_stats_job():
    """Фоновая задача сбора и отправки статистики с логикой повторных попыток"""
    logger.info("Запуск ежедневной утренней рассылки статистики...")

    max_retries = 3
    retry_delay = 5 * 60

    for attempt in range(1, max_retries + 1):
        try:
            async with asynccontextmanager(get_employees_db)() as emp_session:
                async with asynccontextmanager(get_docs_db)() as doc_session:
                    tg_client = TelegramClient(token=bot_settings.TELEGRAM_BOT_TOKEN)
                    service = StatsNotificationService(emp_session, doc_session, tg_client)

                    await service.run_daily_broadcast()
                    logger.info("Утренняя рассылка успешно завершена.")
                    return

        except TelegramNetworkError as net_err:
            # Ловим именно сетевые проблемы Telegram
            logger.warning(
                f"[Попытка {attempt}/{max_retries}] Ошибка сети при рассылке: {net_err}. "
                f"Повтор через {retry_delay // 60} минут..."
            )
            if attempt < max_retries:
                await asyncio.sleep(retry_delay)
            else:
                logger.error("Все попытки утренней рассылки исчерпаны из-за сбоев сети.")

        except Exception as e:
            logger.error(f"Критическая бизнес-ошибка в коде рассылки: {e}", exc_info=True)
            return

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