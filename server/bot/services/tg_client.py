import logging
import httpx

logger = logging.getLogger(__name__)

class TelegramClient:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}/sendMessage"

    async def send_message(self, chat_id: int, text: str) -> bool:
        """Отправка сообщения пользователю с поддержкой MarkdownV2 (или HTML)"""
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.base_url, json=payload, timeout=10.0)
                if response.status_code == 200:
                    return True
                logger.error(f"Ошибка отправки в TG для {chat_id}: {response.text}")
                return False
            except Exception as e:
                logger.exception(f"Сбой соединения с Telegram API для {chat_id}: {e}")
                return False