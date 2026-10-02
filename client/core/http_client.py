# client/core/http_client.py

import base64
import json
import logging
import os
import threading
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import requests
from requests.adapters import HTTPAdapter

logger = logging.getLogger(__name__)

# (connect, read) — быстро понимаем, что сервер недоступен, но не рвём долгие ответы
DEFAULT_TIMEOUT = (5, 30)
UPLOAD_TIMEOUT = (5, 60)


class AuthError(Exception):
    """Ошибка авторизации"""


def _normalize_base_url(base_url: str) -> str:
    """
    localhost -> 127.0.0.1.

    На Windows `localhost` сначала резолвится в IPv6 (::1); uvicorn обычно слушает
    только IPv4, и каждое новое соединение ждёт ~2 секунды, пока не сработает
    откат на IPv4. Keep-alive у uvicorn закрывается через 5 с простоя, поэтому
    задержка возвращалась снова и снова.
    """
    base_url = base_url.rstrip("/")
    try:
        parts = urlsplit(base_url)
        if parts.hostname and parts.hostname.lower() == "localhost":
            netloc = "127.0.0.1" + (f":{parts.port}" if parts.port else "")
            return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    except ValueError:
        pass
    return base_url


def _jwt_expiry(token: str) -> datetime | None:
    """Достаёт exp из JWT (без проверки подписи), чтобы знать реальный срок жизни токена."""
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        exp = payload.get("exp")
        if exp:
            return datetime.fromtimestamp(float(exp))
    except Exception:
        pass
    return None


class HttpClient:
    def __init__(self, base_url: str):
        self.base_url = _normalize_base_url(base_url)
        self.session = requests.Session()
        # Пул соединений: клиент ходит параллельно (ThreadPoolExecutor в загрузчиках)
        adapter = HTTPAdapter(pool_connections=4, pool_maxsize=16)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expiry: datetime | None = None
        # Refresh-токен ротируется сервером: два параллельных refresh с одним токеном
        # ломают сессию, поэтому обновляем строго по одному.
        self._refresh_lock = threading.Lock()

    def set_tokens(self, access_token: str, refresh_token: str, expires_in: int = 3600):
        """Установить токены"""
        self._access_token = access_token
        self._refresh_token = refresh_token
        # Сервер не присылает expires_in, поэтому берём реальный срок из самого JWT.
        self._token_expiry = _jwt_expiry(access_token) or (datetime.now() + timedelta(seconds=expires_in))
        logger.info("Токены установлены. Истекают в %s.", self._token_expiry.strftime("%H:%M:%S"))

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

    def _refresh_access_token(self, failed_token: str | None = None) -> bool:
        """
        Обновить токен доступа.

        failed_token — токен, на котором получили 401. Если пока мы ждали lock,
        другой поток уже обновил токен, повторный refresh не нужен.
        """
        if not self._refresh_token:
            return False

        with self._refresh_lock:
            if failed_token is not None:
                if self._access_token != failed_token:
                    return True  # уже обновлён другим потоком
            elif not self._is_token_expired():
                return True

            try:
                url = f"{self.base_url}/auth/refresh"
                response = self.session.post(
                    url,
                    json={"refresh_token": self._refresh_token},
                    headers={"Content-Type": "application/json"},
                    timeout=DEFAULT_TIMEOUT,
                )

                if response.status_code == 200:
                    data = response.json()
                    self.set_tokens(
                        access_token=data["access_token"],
                        refresh_token=data.get("refresh_token", self._refresh_token),
                        expires_in=data.get("expires_in", 3600),
                    )
                    return True
                logger.error(f"Ошибка обновления токена: {response.status_code} | {response.text[:300]}")
                return False

            except Exception as e:
                logger.exception(f"Ошибка при обновлении токена: {e}")
                return False

    def _auth_header(self) -> dict[str, str]:
        """Authorization-заголовок с автоматическим обновлением токена."""
        if not self._access_token:
            logger.warning("⚠️ Токен отсутствует в запросе!")
            return {}
        if self._is_token_expired():
            logger.info("⏰ Токен истек, обновляем...")
            if not self._refresh_access_token():
                raise AuthError("Не удалось обновить токен")
        return {"Authorization": f"Bearer {self._access_token}"}

    def _get_headers(self) -> dict[str, str]:
        """Получить заголовки для запроса с автоматическим обновлением токена"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "DocumentsClient/1.0",
            # brotli (br) убран: requests без пакета brotli его не распаковывает
            "Accept-Encoding": "gzip, deflate",
        }
        headers.update(self._auth_header())
        return headers

    def _get_multipart_headers(self) -> dict[str, str]:
        """
        Заголовки для multipart/form-data.
        НЕ ставим Content-Type — requests сам выставит boundary.
        НЕ ставим Accept-Encoding: br — requests не умеет распаковывать brotli.
        """
        headers = {"Accept": "*/*"}
        headers.update(self._auth_header())
        return headers

    def _request(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Базовый метод для всех запросов с обработкой ошибок"""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        # Заголовки (там Bearer-токен) в лог не пишем; подробности — только в DEBUG
        logger.debug("📤 %s %s", method, url)
        if kwargs.get("params"):
            logger.debug("📋 Params: %s", kwargs["params"])

        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        try:
            sent_token = self._access_token
            response = self.session.request(method=method, url=url, headers=headers, timeout=DEFAULT_TIMEOUT, **kwargs)

            if response.status_code == 401:
                logger.warning("Получена 401 ошибка, пробуем обновить токен...")
                if self._refresh_access_token(failed_token=sent_token):
                    headers["Authorization"] = f"Bearer {self._access_token}"
                    response = self.session.request(
                        method=method, url=url, headers=headers, timeout=DEFAULT_TIMEOUT, **kwargs
                    )
                else:
                    raise AuthError("Не удалось обновить токен, требуется повторная авторизация")

            if response.status_code == 401:
                raise AuthError("Сессия истекла, требуется повторный вход")

            logger.debug("📥 %s %s -> %s", method, endpoint, response.status_code)

            if response.status_code >= 400:
                logger.error(f"❌ Текст ошибки: {response.text[:500]}")
                raise Exception(f"Ошибка {response.status_code}: {response.text[:200]}")

            if not response.content:
                return {}

            return response.json()

        except requests.RequestException as e:
            logger.exception(f"Ошибка запроса: {e}")
            raise

    # ==================== ОСНОВНЫЕ МЕТОДЫ ====================

    def get(self, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        """GET запрос"""
        return self._request("GET", endpoint, params=params)

    def post(self, endpoint: str, data: dict | None = None, json: dict | None = None) -> dict[str, Any]:
        """POST запрос"""
        return self._request("POST", endpoint, json=json, data=data)

    def put(self, endpoint: str, data: dict | None = None, json: dict | None = None) -> dict[str, Any]:
        """PUT запрос"""
        return self._request("PUT", endpoint, json=json, data=data)

    def patch(self, endpoint: str, data: dict | None = None, json: dict | None = None) -> dict[str, Any]:
        """PATCH запрос"""
        return self._request("PATCH", endpoint, json=json, data=data)

    def delete(self, endpoint: str) -> dict[str, Any]:
        """DELETE запрос"""
        return self._request("DELETE", endpoint)

    def post_file(
        self,
        endpoint: str,
        file_path: str,
        field_name: str = "file",
        extra_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        POST multipart/form-data с файлом (загрузка вложений).
        Content-Type НЕ ставим — requests сам выставит boundary.
        Accept-Encoding НЕ ставим — иначе requests не распакует br.
        """
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
                    timeout=UPLOAD_TIMEOUT,
                )

        logger.info(f"📤 POST (file) {url} — {filename}")

        sent_token = self._access_token
        response = _do_request()

        if response.status_code == 401:
            logger.warning("Получена 401 при загрузке файла, обновляем токен...")
            if not self._refresh_access_token(failed_token=sent_token):
                raise AuthError("Не удалось обновить токен, требуется повторная авторизация")
            response = _do_request()

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

    def post_form(self, endpoint: str, data: dict) -> dict[str, Any]:
        """POST application/x-www-form-urlencoded (для FastAPI Form)."""
        url = f"{self.base_url}{endpoint}"
        headers = {"Accept": "application/json"}
        headers.update(self._auth_header())
        logger.debug("📤 POST (form) %s", url)
        response = self.session.post(url, headers=headers, data=data, timeout=DEFAULT_TIMEOUT)
        if response.status_code >= 400:
            raise Exception(f"Ошибка {response.status_code}: {response.text[:200]}")
        if not response.content:
            return {}
        return response.json()