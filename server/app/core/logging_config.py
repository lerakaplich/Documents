import logging
import sys
from pythonjsonlogger import jsonlogger


def setup_logging(debug: bool = False) -> None:
    """Настройка корневого логгера для вывода JSON в stdout."""
    log_level = logging.DEBUG if debug else logging.INFO

    # Handler для вывода в консоль (Docker читает stdout)
    stream_handler = logging.StreamHandler(sys.stdout)

    # Стандартный JSON-форматтер
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    stream_handler.setFormatter(formatter)

    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Очищаем старые хендлеры, если они были
    root_logger.handlers.clear()
    root_logger.addHandler(stream_handler)

    # Приглушаем слишком частый встроенный логгер uvicorn.access,
    # так как наше Middleware будет логировать запросы подробнее
    logging.getLogger("uvicorn.access").disabled = True