import os

from pydantic import BaseModel


class BotSettings(BaseModel):
    # Токен бота (берём из переменных окружения или ставим дефолт)
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "8108629062:AAFFRoG-fmL_X2UNM4JZUQCRLL200Qt61Hc")

    # Время рассылки статистики (по умолчанию 09:00)
    STATS_SEND_HOUR: int = int(os.getenv("STATS_SEND_HOUR", 9))
    STATS_SEND_MINUTE: int = int(os.getenv("STATS_SEND_MINUTE", 0))

    # Часовой пояс
    BOT_TIMEZONE: str = os.getenv("BOT_TIMEZONE", "Europe/Minsk")


bot_settings = BotSettings()

