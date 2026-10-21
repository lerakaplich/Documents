from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from server.app.config import VERSION_FILE, UPDATES_DIR, UPDATE_FILENAME
from server.app.schemas.version import VersionCheckResponse

router = APIRouter(prefix="/version", tags=["App Updates"])

@router.get("/check", response_model=VersionCheckResponse, summary="Проверить наличие новой версии")
async def check_version():
    # 1. Читаем версию из файла на диске (если файла нет, ставим дефолтную)
    if VERSION_FILE.exists():
        latest_version = VERSION_FILE.read_text(encoding="utf-8").strip()
    else:
        latest_version = "1.0.0"

    # 2. Проверяем файл архива и считаем его размер
    file_path = UPDATES_DIR / UPDATE_FILENAME
    file_size = None
    if file_path.exists():
        file_size = round(file_path.stat().st_size / (1024 * 1024), 2)

    return VersionCheckResponse(
        latest_version=latest_version,
        min_required_version="1.0.0",  # Можно тоже вынести в файл, если нужно
        download_url="/api/version/download",
        release_notes="Вышло новое обновление системы СЭД.",
        file_size_mb=file_size
    )


@router.get("/download", summary="Скачать файл обновления")
async def download_update():
    file_path = UPDATES_DIR / UPDATE_FILENAME

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл обновления не найден на сервере."
        )

    return FileResponse(
        path=file_path,
        filename=UPDATE_FILENAME,
        media_type="application/octet-stream"
    )