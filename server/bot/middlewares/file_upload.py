import tempfile
from typing import cast, BinaryIO

from fastapi import UploadFile
from starlette.datastructures import Headers


class TelegramUploadFile(UploadFile):
    """
    Адаптер бинарных данных Telegram под интерфейс UploadFile для FastAPI/Starlette.
    """
    def __init__(self, file_bytes: bytes, filename: str, content_type: str = "application/octet-stream"):
        # Создаем временный файл в памяти/диске, как это делает FastAPI
        temp_file = tempfile.SpooledTemporaryFile(max_size=10 * 1024 * 1024)
        temp_file.write(file_bytes)
        temp_file.seek(0)

        # Оборачиваем словарик заголовков в Starlette Headers
        headers = Headers({"content-type": content_type})

        super().__init__(
            file=cast(BinaryIO, temp_file),
            filename=filename,
            headers=headers
        )