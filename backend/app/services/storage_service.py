import asyncio
import hashlib
import mimetypes
from dataclasses import dataclass
from typing import Any, cast

import boto3  # pyright: ignore[reportMissingTypeStubs]
from botocore.exceptions import (  # pyright: ignore[reportMissingTypeStubs]
    BotoCoreError,
    ClientError,
)

from app.core.config import Settings
from app.core.exceptions import (
    StorageDeleteFailed,
    StorageDownloadFailed,
    StorageUploadFailed,
)


@dataclass
class StoredObject:
    key: str
    etag: str | None
    mime_type: str
    size_bytes: int
    sha256: str


class StorageService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client: Any = cast(Any, boto3).client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.SIP_S3_FILES_ACCESS_KEY,
            aws_secret_access_key=settings.SIP_S3_FILES_SECRET_KEY,
        )

    def _normalize_mime_type(
        self, filename: str, content_type: str | None = None
    ) -> str:
        if content_type:
            return content_type
        guessed_type, _ = mimetypes.guess_type(filename)
        return guessed_type or "application/octet-stream"

    def compute_sha256(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    async def upload_bytes(
        self,
        key: str,
        content: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> StoredObject:
        mime_type = self._normalize_mime_type(filename, content_type)

        def _upload() -> dict[str, Any]:
            return self.client.put_object(
                Bucket=self.settings.SIP_S3_FILES_BUCKET,
                Key=key,
                Body=content,
                ContentType=mime_type,
            )

        try:
            response = await asyncio.to_thread(_upload)
        except (BotoCoreError, ClientError) as error:
            raise StorageUploadFailed(f"upload_bytes:{key}:{error.__class__.__name__}")

        return StoredObject(
            key=key,
            etag=str(response.get("ETag", "")).strip('"') or None,
            mime_type=mime_type,
            size_bytes=len(content),
            sha256=self.compute_sha256(content),
        )

    async def delete_object(self, key: str) -> None:
        def _delete() -> None:
            self.client.delete_object(Bucket=self.settings.SIP_S3_FILES_BUCKET, Key=key)

        try:
            await asyncio.to_thread(_delete)
        except (BotoCoreError, ClientError) as error:
            raise StorageDeleteFailed(f"delete_object:{key}:{error.__class__.__name__}")

    async def download_bytes(self, key: str) -> bytes:
        def _download() -> bytes:
            response = self.client.get_object(
                Bucket=self.settings.SIP_S3_FILES_BUCKET,
                Key=key,
            )
            return cast(bytes, response["Body"].read())

        try:
            return await asyncio.to_thread(_download)
        except (BotoCoreError, ClientError) as error:
            raise StorageDownloadFailed(
                f"download_bytes:{key}:{error.__class__.__name__}"
            )

    async def generate_download_url(self, key: str, filename: str) -> str:
        def _presign() -> str:
            return cast(
                str,
                self.client.generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": self.settings.SIP_S3_FILES_BUCKET,
                        "Key": key,
                        "ResponseContentDisposition": f'attachment; filename="{filename}"',
                    },
                    ExpiresIn=self.settings.S3_PRESIGN_EXPIRY_SECONDS,
                ),
            )

        return await asyncio.to_thread(_presign)
