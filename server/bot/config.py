from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    TELEGRAM_BOT_TOKEN: str
    SUPPORT_CHAT_ID: int

    STATS_SEND_HOUR: int = 9
    STATS_SEND_MINUTE: int = 0
    BOT_TIMEZONE: str = "Europe/Minsk"


# Создаем экземпляр настроек
bot_settings = BotSettings()