# client/services/service_factory.py
from typing import Optional

from client.core.config import config
from client.core.http_client import HttpClient
from client.services.auth_service import AuthService
from client.services.employee_service import EmployeeService
from client.services.org_service import OrgService


class ServiceFactory:
    """Фабрика для создания сервисов с общим HTTP клиентом"""

    _instance = None
    _http_client: HttpClient = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def init(cls, base_url: Optional[str] = None):
        """
        Инициализация фабрики с базовым URL

        Args:
            base_url: Базовый URL сервера. Если не указан, берется из config
        """
        if cls._http_client is None:
            url = base_url or config.base_url
            cls._http_client = HttpClient(url)

    @classmethod
    def get_http_client(cls) -> HttpClient:
        """Получить HTTP клиент"""
        if cls._http_client is None:
            cls.init()  # Инициализируем с параметрами по умолчанию
        return cls._http_client

    @classmethod
    def get_auth_service(cls) -> AuthService:
        """Получить сервис авторизации"""
        return AuthService(cls.get_http_client())

    @classmethod
    def get_employee_service(cls) -> EmployeeService:
        """Получить сервис сотрудников"""
        return EmployeeService(cls.get_http_client())

    @classmethod
    def get_org_service(cls) -> OrgService:
        """Получить сервис организаций"""
        return OrgService(cls.get_http_client())

    @classmethod
    def set_tokens(cls, access_token: str, refresh_token: str, expires_in: int = 3600):
        """Установить токены в HTTP клиенте"""
        cls.get_http_client().set_tokens(access_token, refresh_token, expires_in)

    @classmethod
    def clear_tokens(cls):
        """Очистить токены"""
        cls.get_http_client().clear_tokens()