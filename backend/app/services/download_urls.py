from app.models.storage import StoredFile
from app.services.storage_service import StorageService


class DownloadUrls:
    def __init__(self, storage_service: StorageService) -> None:
        self.storage_service = storage_service
        self._by_storage_key: dict[str, str] = {}

    async def of(self, stored_file: StoredFile | None) -> str | None:
        if stored_file is None:
            return None
        cached = self._by_storage_key.get(stored_file.storage_key)
        if cached is not None:
            return cached
        url = await self.storage_service.generate_download_url(
            stored_file.storage_key, stored_file.original_filename
        )
        self._by_storage_key[stored_file.storage_key] = url
        return url
