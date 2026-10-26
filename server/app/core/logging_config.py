import logging
import os
from logging.handlers import RotatingFileHandler
from pythonjsonlogger import jsonlogger

def setup_logging(debug: bool = False) -> None:
    """Настройка корневого логгера для вывода JSON в файл с ротацией."""
    log_level = logging.DEBUG if debug else logging.INFO

    # Создаем папку для логов рядом с приложением/exe
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "server.log")

    # Файловый обработчик с ротацией (макс 5 МБ, до 5 архивов), кодировка UTF-8
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )

    # Используем ваш родной JSON-форматтер из python-json-logger
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    file_handler.setFormatter(formatter)

    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Очищаем старые хендлеры и добавляем наш файловый
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)

    # Приглушаем встроенный логгер uvicorn.access, чтобы не было дублирующих логов,
    # так как ваше Middleware уже логирует запросы подробно.
    logging.getLogger("uvicorn.access").disabled = True

    # Перенаправляем остальные логгеры uvicorn и fastapi в тот же файл
    for logger_name in ("uvicorn", "uvicorn.error", "fastapi"):
        l = logging.getLogger(logger_name)
        l.handlers.clear()
        l.handlers.append(file_handler)
        l.propagate = False