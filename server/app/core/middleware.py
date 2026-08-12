import logging
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger("http.access")


class LoggingAndTraceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()

        # 1. Извлекаем или генерируем Correlation ID (Trace ID)
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

        # Сохраняем в state запроса, чтобы сервисный слой при необходимости мог его прочитать
        request.state.correlation_id = correlation_id

        # Базовые метаданные запроса
        extra_data = {
            "correlation_id": correlation_id,
            "http_method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }

        try:
            # 2. Выполняем запрос
            response = await call_next(request)
            process_time = time.perf_counter() - start_time

            # Добавляем данные об ответе
            extra_data["status_code"] = response.status_code
            extra_data["duration_ms"] = round(process_time * 1000, 2)

            # Выбираем уровень лога в зависимости от HTTP-статуса
            if response.status_code >= 500:
                logger.error(
                    f"HTTP {request.method} {request.url.path} finished with server error {response.status_code}",
                    extra=extra_data,
                )
            elif response.status_code >= 400:
                logger.warning(
                    f"HTTP {request.method} {request.url.path} finished with client error {response.status_code}",
                    extra=extra_data,
                )
            else:
                logger.info(
                    f"HTTP {request.method} {request.url.path} finished successfully ({response.status_code})",
                    extra=extra_data,
                )

            # 3. Пробрасываем Correlation-ID дальше в ответ клиенту
            response.headers["X-Correlation-ID"] = correlation_id
            return response

        except Exception as exc:
            # 4. Перехватываем необработанные 500-е ошибки (падения)
            process_time = time.perf_counter() - start_time
            extra_data["duration_ms"] = round(process_time * 1000, 2)
            extra_data["exception_type"] = type(exc).__name__

            logger.error(
                f"HTTP {request.method} {request.url.path} failed with unhandled exception: {exc}",
                exc_info=True,
                extra=extra_data,
            )
            raise exc