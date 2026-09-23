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
                logger.error(f"Ошибка обновления токена: {response.status_code} | {response.text[:300]}")
                return False

        except Exception as e:
            logger.error(f"Ошибка при обновлении токена: {e}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Получить заголовки для запроса с автоматическим обновлением токена"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "DocumentsClient/1.0",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }

        if self._access_token:
            if self._is_token_expired():
                logger.info("⏰ Токен истек, обновляем...")
                if not self._refresh_access_token():
                    raise AuthError("Не удалось обновить токен")
            headers["Authorization"] = f"Bearer {self._access_token}"
            logger.debug(f"🔑 Используется токен: {self._access_token[:20]}...")
        else:
            logger.warning("⚠️ Токен отсутствует в запросе!")

        return headers

    def _get_multipart_headers(self) -> Dict[str, str]:
        """
        Заголовки для multipart/form-data.
        НЕ ставим Content-Type — requests сам выставит boundary.
        НЕ ставим Accept-Encoding: br — requests не умеет распаковывать brotli.
        """
        headers = {
            "Accept": "*/*",
        }
        if self._access_token:
            if self._is_token_expired():
                logger.info("⏰ Токен истек, обновляем...")
                if not self._refresh_access_token():
                    raise AuthError("Не удалось обновить токен")
            headers["Authorization"] = f"Bearer {self._access_token}"
        else:
            logger.warning("⚠️ Токен отсутствует в запросе!")
        return headers

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Базовый метод для всех запросов с обработкой ошибок"""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        # Логируем запрос
        logger.info(f"📤 {method} {url}")
        logger.info(f"📋 Headers: {headers}")

        if "json" in kwargs and kwargs["json"]:
            logger.debug(f"📦 Body: {kwargs['json']}")
        if "params" in kwargs and kwargs["params"]:
            logger.debug(f"📋 Params: {kwargs['params']}")

        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        try:
            # Явно передаем все параметры
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                timeout=30,
                **kwargs
            )

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

            # Логируем ответ
            logger.info(f"📥 Статус ответа: {response.status_code}")
            if response.status_code >= 400:
                logger.error(f"❌ Текст ошибки: {response.text[:500]}")

            if response.status_code >= 400:
                logger.error(f"❌ Текст ошибки: {response.text[:500]}")
                raise Exception(f"Ошибка {response.status_code}: {response.text[:200]}")



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

    def post_file(self, endpoint: str, file_path: str, field_name: str = "file",
                  extra_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        POST multipart/form-data с файлом (загрузка вложений).
        Content-Type НЕ ставим — requests сам выставит boundary.
        Accept-Encoding НЕ ставим — иначе requests не распакует br.
        """
        import os

        url = f"{self.base_url}{endpoint}"
        filename = os.path.basename(file_path)

        def _do_request() -> requests.Response:
            with open(file_path, "rb") as f:
                files = {field_name: (filename, f, "application/octet-stream")}
                return self.session.request(
                    method="POST",
                    url=url,
                    headers=self._get_multipart_headers(),
                    files=files,
                    data=extra_data or {},
                    timeout=60,
                )

        logger.info(f"📤 POST (file) {url} — {filename}")

        response = _do_request()

        if response.status_code == 401:
            logger.warning("Получена 401 при загрузке файла, обновляем токен...")
            if not self._refresh_access_token():
                raise AuthError("Не удалось обновить токен, требуется повторная авторизация")
            response = _do_request()

        # ДИАГНОСТИКА — увидишь, что реально ушло
        logger.info(f"📋 Фактический URL: {response.request.url}")
        logger.info(f"📋 Фактические заголовки: {dict(response.request.headers)}")
        logger.info(f"📥 Статус ответа (file): {response.status_code}")

        if response.status_code >= 400:
            body = response.text[:500] if response.content else "<empty>"
            logger.error(f"❌ Текст ошибки: {body}")
            raise Exception(f"Ошибка {response.status_code}: {body}")

        if not response.content:
            return {"ok": True}

        try:
            data = response.json()
        except ValueError:
            logger.warning(f"Ответ не JSON: {response.text[:200]}")
            return {"ok": True}

        if data is None:
            # сервер вернул literal null — это успех
            return {"ok": True}

        return data