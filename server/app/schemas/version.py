from pydantic import BaseModel


class VersionCheckResponse(BaseModel):
    latest_version: str
    min_required_version: str
    download_url: str
    release_notes: str
    file_size_mb: float | None = None