# server/bot/config.py
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

# .env ищем рядом с проектом, независимо от cwd.
# config.py лежит в server/bot/, значит корень проекта — на два уровня выше.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Не задана переменная окружения {name}")
    return value


class BotSettings(BaseModel):
    TELEGRAM_BOT_TOKEN: str
    STATS_SEND_HOUR: int = 9
    STATS_SEND_MINUTE: int = 0
    BOT_TIMEZONE: str = "Europe/Minsk"
    SUPPORT_CHAT_ID: int = -1004416230667


bot_settings = BotSettings(
    TELEGRAM_BOT_TOKEN=_require_env("TELEGRAM_BOT_TOKEN"),
    STATS_SEND_HOUR=int(os.getenv("STATS_SEND_HOUR", 9)),
    STATS_SEND_MINUTE=int(os.getenv("STATS_SEND_MINUTE", 0)),
    BOT_TIMEZONE=os.getenv("BOT_TIMEZONE", "Europe/Minsk"),
    SUPPORT_CHAT_ID=int(os.getenv("SUPPORT_CHAT_ID", -1004416230667)),
)