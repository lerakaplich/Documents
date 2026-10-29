# client/core/http_client.py

import base64
import json
import logging
import os
import threading
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

import requests
from requests.adapters import HTTPAdapter
from urllib3.exceptions import ConnectTimeoutError, MaxRetryError, NewConnectionError, ReadTimeoutError
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# (connect, read) — быстро понимаем, что сервер недоступен, но не рвём долгие ответы
DEFAULT_TIMEOUT = (5, 30)
UPLOAD_TIMEOUT = (5, 60)


class AuthError(Exception):
    """Ошибка авторизации"""


class ApiError(Exception):
    """
    HTTP-ошибка сервера (status >= 400).

    Наследуется от Exception и сохраняет прежний текст сообщения
    «Ошибка <код>: <тело>», поэтому существующий код `except Exception`
    продолжает работать, а новый может проверять `e.status_code`
    (например, молча обработать 404 вместо трейсбека).
    """

    def __init__(self, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(f"Ошибка {status_code}: {body}")


class ServerUnavailableError(requests.exceptions.ConnectionError):
    """
    Сервер не ответил: таймаут или нет соединения.

    Наследует requests.ConnectionError, поэтому существующий код с
    `except requests.ConnectionError` / `except Exception` работает как раньше,
    но сообщение короткое и без цепочки urllib3 на сотню строк в логе.
    """


def _network_error_text(e: requests.RequestException) -> str:
    """Человекочитаемая причина сетевой ошибки (requests прячет её внутри MaxRetryError)."""
    reason = e.args[0].reason if e.args and isinstance(e.args[0], MaxRetryError) else None
    if isinstance(e, requests.ReadTimeout) or isinstance(reason, ReadTimeoutError):
        return f"сервер принял запрос, но не ответил за {DEFAULT_TIMEOUT[1]} с"
    # NewConnectionError в urllib3 2.x — подкласс ConnectTimeoutError, поэтому проверяем его первым
    if isinstance(reason, NewConnectionError):
        return "нет соединения с сервером (отказ в подключении или нет маршрута)"
    if isinstance(e, requests.ConnectTimeout) or isinstance(reason, ConnectTimeoutError):
        return f"не удалось подключиться за {DEFAULT_TIMEOUT[0]} с"
    return "нет соединения с сервером"


class _ApiJSONEncoder(json.JSONEncoder):
    """
    Сериализатор для JSON-тела запросов.

    requests умеет сам сериализовать dict, но `date`, `datetime`, `Decimal`,
    `UUID` он не знает и падает с TypeError: Object of type date is not JSON
    serializable. Здесь приводим их к ISO-строкам/числам, которые ожидает
    Pydantic на сервере.
    """

    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)


def _json_dumps(obj: Any) -> str:
    """Дамп в JSON с поддержкой date/datetime/Decimal/UUID."""
    return json.dumps(obj, cls=_ApiJSONEncoder, ensure_ascii=False)


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


CACHEABLE_PREFIXES = ("/org", "/doc-types", "/tag", "/employees/all")
CACHE_TTL = 60  # секунд

class HttpClient:
    def __init__(self, base_url: str):
        self.base_url = _normalize_base_url(base_url)
        self.session = requests.Session()
        # Пул соединений: клиент ходит параллельно (ThreadPoolExecutor в загрузчиках)
        # Повторяем ТОЛЬКО неудачные подключения (connect timeout / refused): запрос
        # при этом на сервер не уходил, поэтому повтор безопасен даже для POST.
        # Раньше один потерянный SYN = ошибка входа, и пользователю приходилось
        # нажимать «Войти» второй раз.
        retry = Retry(
            total=None,
            connect=2,
            read=0,
            status=0,
            redirect=0,
            backoff_factor=0.5,
            allowed_methods=None,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=retry)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expiry: datetime | None = None
        # Refresh-токен ротируется сервером: два параллельных refresh с одним токеном
        # ломают сессию, поэтому обновляем строго по одному.
        self._refresh_lock = threading.Lock()
        # в __init__
        self._cache: dict[tuple, tuple[float, Any]] = {}
        self._inflight: dict[tuple, threading.Event] = {}
        self._failures: dict[tuple, tuple[float, BaseException]] = {}
        self._cache_lock = threading.Lock()



    def get_cached(self, endpoint: str, params: dict | None = None, ttl: float = CACHE_TTL):
        import time
        key = (endpoint, tuple(sorted((k, repr(v)) for k, v in (params or {}).items())))
        while True:
            with self._cache_lock:
                hit = self._cache.get(key)
                if hit and time.monotonic() - hit[0] < ttl:
                    return hit[1]
                event = self._inflight.get(key)
                if event is None:
                    self._inflight[key] = threading.Event()
                    break
            started = time.monotonic()
            event.wait(timeout=30)  # ждём чужой запрос и повторяем проверку кэша
            with self._cache_lock:
                failure = self._failures.get(key)
            if failure and failure[0] >= started:
                # Чужой запрос упал, пока мы ждали — повторять его по очереди (каждый до 30 с) нет смысла
                raise failure[1]
        try:
            result = self.get(endpoint, params)
            with self._cache_lock:
                self._cache[key] = (time.monotonic(), result)
                self._failures.pop(key, None)
            return result
        except Exception as e:
            with self._cache_lock:
                self._failures[key] = (time.monotonic(), e)
            raise
        finally:
            with self._cache_lock:
                self._inflight.pop(key).set()

    def invalidate_cache(self, prefix: str = ""):
        with self._cache_lock:
            for k in [k for k in self._cache if k[0].startswith(prefix)]:
                del self._cache[k]

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

    def _auth_header(self, quiet: bool = False) -> dict[str, str]:
        """
        Authorization-заголовок с автоматическим обновлением токена.

        quiet=True — не warn-ить об отсутствии токена (логин и другие /auth/*
        запросы по определению идут без токена).
        """
        if not self._access_token:
            if not quiet:
                logger.warning("⚠️ Токен отсутствует в запросе!")
            return {}
        if self._is_token_expired():
            logger.info("⏰ Токен истек, обновляем...")
            if not self._refresh_access_token():
                raise AuthError("Не удалось обновить токен")
        return {"Authorization": f"Bearer {self._access_token}"}

    def _get_headers(self, quiet_no_token: bool = False) -> dict[str, str]:
        """Получить заголовки для запроса с автоматическим обновлением токена"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "DocumentsClient/1.0",
            # brotli (br) убран: requests без пакета brotli его не распаковывает
            "Accept-Encoding": "gzip, deflate",
        }
        headers.update(self._auth_header(quiet=quiet_no_token))
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
        headers = self._get_headers(quiet_no_token=endpoint.startswith("/auth/"))

        # ── Превращаем json=payload в data=<строка>, чтобы поддержать date/datetime ──
        if "json" in kwargs and kwargs["json"] is not None:
            payload = kwargs.pop("json")
            kwargs["data"] = _json_dumps(payload)
            # Content-Type уже стоит в headers (_get_headers)

        logger.debug("📤 %s %s", method, url)
        if kwargs.get("params"):
            logger.debug("📋 Params: %s", kwargs["params"])

        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        try:
            sent_token = self._access_token
            response = self.session.request(method=method, url=url, headers=headers, timeout=DEFAULT_TIMEOUT, **kwargs)

            # 401 без токена (например, неверный пароль при логине) — это не «протух
            # токен»: refresh бессмыслен, показываем настоящий ответ сервера.
            if response.status_code == 401 and sent_token is None:
                # Ожидаемая ситуация (неверный пароль, протухший/удалённый на сервере
                # refresh_token) — не ошибка клиента, поэтому warning, а не error.
                logger.warning("401 %s: %s", endpoint, self._error_detail(response))
                raise AuthError(self._error_detail(response))

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
                logger.error("❌ %s %s -> %s: %s", method, endpoint, response.status_code, response.text[:500])
                raise ApiError(response.status_code, response.text[:200])

            if not response.content:
                return {}

            return response.json()

        except (requests.ConnectionError, requests.Timeout) as e:
            # Сервер недоступен или не ответил — трейсбек на 100 строк ничего не добавляет.
            text = _network_error_text(e)
            logger.error("Сервер недоступен (%s %s): %s", method, url, text)
            raise ServerUnavailableError(f"Сервер недоступен: {text}") from None
        except requests.RequestException as e:
            logger.exception(f"Ошибка запроса: {e}")
            raise

    @staticmethod
    def _error_detail(response: requests.Response) -> str:
        """Достаёт человекочитаемый detail из JSON-ответа FastAPI."""
        try:
            detail = response.json().get("detail")
            if isinstance(detail, str) and detail:
                return detail
        except Exception:
            pass
        return f"Ошибка {response.status_code}: {response.text[:200]}"

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

    def get_binary(self, endpoint: str, params: dict | None = None) -> bytes:
        """
        GET с бинарным ответом (JPEG-страницы вложений и т.п.).
        Те же правила, что у _request: авто-refresh токена, один повтор при 401,
        ApiError при status >= 400.
        """
        url = f"{self.base_path_url(endpoint)}"
        headers = {"Accept": "*/*", "Accept-Encoding": "gzip, deflate"}
        headers.update(self._auth_header())
        sent_token = self._access_token
        try:
            response = self.session.get(url, headers=headers, params=params, timeout=DEFAULT_TIMEOUT)
            if response.status_code == 401 and sent_token is not None:
                if not self._refresh_access_token(failed_token=sent_token):
                    raise AuthError("Не удалось обновить токен, требуется повторная авторизация")
                headers["Authorization"] = f"Bearer {self._access_token}"
                response = self.session.get(url, headers=headers, params=params, timeout=DEFAULT_TIMEOUT)
        except (requests.ConnectionError, requests.Timeout) as e:
            text = _network_error_text(e)
            logger.error("Сервер недоступен (GET %s): %s", url, text)
            raise ServerUnavailableError(f"Сервер недоступен: {text}") from None
        if response.status_code == 401:
            raise AuthError("Сессия истекла, требуется повторный вход")
        if response.status_code >= 400:
            logger.error("❌ GET %s -> %s: %s", endpoint, response.status_code, response.text[:300])
            raise ApiError(response.status_code, response.text[:200])
        return response.content

    def base_path_url(self, endpoint: str) -> str:
        return f"{self.base_url}{endpoint}"

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
            raise ApiError(response.status_code, body)

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
        headers.update(self._auth_header(quiet=endpoint.startswith("/auth/")))
        logger.debug("📤 POST (form) %s", url)
        sent_token = self._access_token
        response = self.session.post(url, headers=headers, data=data, timeout=DEFAULT_TIMEOUT)

        if response.status_code == 401 and sent_token is not None:
            # как и в _request: токен мог протухнуть — обновляем и повторяем один раз
            if not self._refresh_access_token(failed_token=sent_token):
                raise AuthError("Не удалось обновить токен, требуется повторная авторизация")
            headers["Authorization"] = f"Bearer {self._access_token}"
            response = self.session.post(url, headers=headers, data=data, timeout=DEFAULT_TIMEOUT)

        if response.status_code >= 400:
            raise ApiError(response.status_code, response.text[:200])
        if not response.content:
            return {}
        return response.json()