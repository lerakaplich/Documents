from typing import Optional, Dict, Any
from client.core.http_client import HttpClient
from client.services.auth_service import AuthService
from client.services.employee_service import EmployeeService
from client.core.config import config
import logging

logger = logging.getLogger(__name__)


class AppState:
    """Глобальное состояние приложения"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.base_url = config.base_url
        print(f"✅ Base URL: {self.base_url}")

        self.http_client = HttpClient(self.base_url)
        self.auth_service = AuthService(self.http_client)
        self.employee_service = EmployeeService(self.http_client)
        self.current_user: Optional[Dict[str, Any]] = None
        self.is_authenticated = False

    def set_user(self, user_data: Dict[str, Any]):
        """Установить данные текущего пользователя"""
        self.current_user = user_data
        self.is_authenticated = True
        logger.info(f"Пользователь авторизован: {user_data.get('full_name', 'Unknown')}")

    def clear_user(self):
        """Очистить данные пользователя"""
        self.current_user = None
        self.is_authenticated = False
        self.http_client.clear_tokens()
        logger.info("Пользователь деавторизован")

