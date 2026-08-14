# client/core/http_client.py

import requests
from typing import Optional, Dict, Any
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Ошибка авторизации"""
    pass


class HttpClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    def set_tokens(self, access_token: str, refresh_token: str, expires_in: int = 3600):
        """Установить токены"""
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._token_expiry = datetime.now() + timedelta(seconds=expires_in)
        logger.info(f"Токены установлены. Истекают через {expires_in} сек.")

    def clear_tokens(self):
        """Очистить токены (выход из системы)"""
        self._access_token = None
        self._refresh_token = None
        self._token_expiry = None

    def _is_token_expired(self) -> bool:
        """Проверить, истек ли токен"""
        if not self._token_expiry:
            return True
        return datetime.now() >= self._token_expiry - timedelta(seconds=30)

    def _refresh_access_token(self) -> bool:
        """Обновить токен доступа"""
        if not self._refresh_token:
            return False

        try:
            url = f"{self.base_url}/auth/refresh"
            response = self.session.post(
                url,
                json={"refresh_token": self._refresh_token},
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                data = response.json()
                self.set_tokens(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token", self._refresh_token),
                    expires_in=data.get("expires_in", 3600)
                )
                return True
            else:
                logger.error(f"Ошибка обновления токена: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Ошибка при обновлении токена: {e}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Получить заголовки для запроса с автоматическим обновлением токена"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        if self._access_token:
            if self._is_token_expired():
                logger.info("Токен истек, обновляем...")
                if not self._refresh_access_token():
                    raise AuthError("Не удалось обновить токен")
            headers["Authorization"] = f"Bearer {self._access_token}"

        return headers

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Базовый метод для всех запросов с обработкой ошибок"""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        try:
            response = self.session.request(method, url, headers=headers, **kwargs)

            if response.status_code == 401:
                logger.warning("Получена 401 ошибка, пробуем обновить токен...")
                if self._refresh_access_token():
                    headers["Authorization"] = f"Bearer {self._access_token}"
                    response = self.session.request(method, url, headers=headers, **kwargs)
                    if response.status_code != 401:
                        logger.info("Запрос повторно выполнен успешно")
                else:
                    raise AuthError("Не удалось обновить токен, требуется повторная авторизация")

            if response.status_code == 401:
                raise AuthError("Сессия истекла, требуется повторный вход")

            response.raise_for_status()

            if not response.content:
                return {}

            return response.json()

        except requests.RequestException as e:
            logger.error(f"Ошибка запроса: {e}")
            raise

    # ==================== ОСНОВНЫЕ МЕТОДЫ ====================

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """GET запрос"""
        return self._request("GET", endpoint, params=params)

    def post(self, endpoint: str, data: Optional[Dict] = None, json: Optional[Dict] = None) -> Dict[str, Any]:
        """POST запрос"""
        return self._request("POST", endpoint, json=json, data=data)

    def put(self, endpoint: str, data: Optional[Dict] = None, json: Optional[Dict] = None) -> Dict[str, Any]:
        """PUT запрос"""
        return self._request("PUT", endpoint, json=json, data=data)

    def patch(self, endpoint: str, data: Optional[Dict] = None, json: Optional[Dict] = None) -> Dict[str, Any]:
        """PATCH запрос"""
        return self._request("PATCH", endpoint, json=json, data=data)

    def delete(self, endpoint: str) -> Dict[str, Any]:
        """DELETE запрос"""
        return self._request("DELETE", endpoint)