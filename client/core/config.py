import os
from typing import Optional


class ClientConfig:
    """Конфигурация клиента"""

    # URL сервера
    SERVER_HOST = os.getenv("SERVER_HOST", "localhost")
    SERVER_PORT = os.getenv("SERVER_PORT", "8000")
    API_VERSION = os.getenv("API_VERSION", "v1")

    @property
    def base_url(self) -> str:
        return f"http://{self.SERVER_HOST}:{self.SERVER_PORT}/api/{self.API_VERSION}"

    # Singleton
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


# Создаем глобальный экземпляр
config = ClientConfig()