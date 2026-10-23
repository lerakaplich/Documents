import asyncio
import logging
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence

from aiogram import Bot

from server.app.services.tiff.tiff_converter import DocumentProcessor

logger = logging.getLogger("bot_photo_tiff")


@dataclass(frozen=True)
class TiffResult:
    data: bytes
    filename: str
    pages: int


class PhotoTiffService:
    """Скачивает фото из Telegram и собирает из них многостраничный TIFF."""

    def __init__(self, processor: DocumentProcessor | None = None):
        self._processor = processor or DocumentProcessor()

    async def build_tiff(self, bot: Bot, file_ids: Sequence[str]) -> TiffResult:
        with tempfile.TemporaryDirectory(prefix="photo_tiff_") as tmp:
            workdir = Path(tmp)

            sources: list[str] = []
            for index, file_id in enumerate(file_ids, start=1):
                path = workdir / f"page_{index:03d}"
                await bot.download(file_id, destination=path)
                sources.append(str(path))

            output = workdir / "result.tiff"
            # Pillow — CPU-bound, не блокируем event loop бота
            await asyncio.to_thread(
                self._processor.convert_images_to_tiff, sources, str(output)
            )
            data = output.read_bytes()

        filename = f"scan_{datetime.now():%Y%m%d_%H%M%S}.tiff"
        logger.info("TIFF built: %s pages, %s bytes", len(file_ids), len(data))
        return TiffResult(data=data, filename=filename, pages=len(file_ids))