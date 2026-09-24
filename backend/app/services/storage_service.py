import asyncio
import hashlib
import mimetypes
from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from typing import Any, Protocol, cast

import boto3
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
)

from app.core.config import Settings
from app.core.downloads import content_disposition_attachment
from app.core.exceptions import (
    StorageDeleteFailed,
    StorageDownloadFailed,
    StorageFileInvalidMimeType,
    StorageFileTooLarge,
    StorageUploadFailed,
)

UPLOAD_CHUNK_SIZE_BYTES = 1024 * 1024

IMAGE_OR_PDF_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "application/pdf",
}


class UploadKind(Enum):
    IMAGE = "image"
    PDF = "pdf"
    VIDEO = "video"
    FILE = "file"


class UploadStream(Protocol):
    async def read(self, size: int = -1, /) -> bytes: ...


@dataclass(frozen=True)
class MimeSignature:
    mime_type: str
    markers: tuple[tuple[int, bytes], ...]


MIME_SIGNATURES = (
    MimeSignature("image/png", ((0, b"\x89PNG\r\n\x1a\n"),)),
    MimeSignature("image/jpeg", ((0, b"\xff\xd8\xff"),)),
    MimeSignature("image/gif", ((0, b"GIF87a"),)),
    MimeSignature("image/gif", ((0, b"GIF89a"),)),
    MimeSignature("image/webp", ((0, b"RIFF"), (8, b"WEBP"))),
    MimeSignature("application/pdf", ((0, b"%PDF-"),)),
    MimeSignature("image/heic", ((4, b"ftypheic"),)),
    MimeSignature("image/heic", ((4, b"ftypheix"),)),
    MimeSignature("image/heic", ((4, b"ftypmif1"),)),
    MimeSignature("image/avif", ((4, b"ftypavif"),)),
    MimeSignature("video/quicktime", ((4, b"ftypqt"),)),
    MimeSignature("video/quicktime", ((4, b"moov"),)),
    MimeSignature("video/mp4", ((4, b"ftyp"),)),
    MimeSignature("video/webm", ((0, b"\x1a\x45\xdf\xa3"),)),
)


def sniff_mime_type(content: bytes) -> str | None:
    for signature in MIME_SIGNATURES:
        if all(
            content.startswith(magic, offset) for offset, magic in signature.markers
        ):
            return signature.mime_type
    return None


@dataclass
class StoredObject:
    key: str
    etag: str | None
    mime_type: str
    size_bytes: int
    sha256: str


def s3_client(settings: Settings, endpoint_url: str) -> Any:
    return cast(Any, boto3).client(
        "s3",
        endpoint_url=endpoint_url,
        region_name=settings.S3_REGION,
        aws_access_key_id=settings.SIP_S3_FILES_ACCESS_KEY,
        aws_secret_access_key=settings.SIP_S3_FILES_SECRET_KEY,
    )


class StorageService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client: Any = s3_client(settings, settings.S3_ENDPOINT_URL)

    @cached_property
    def presign_client(self) -> Any:
        public_endpoint_url = self.settings.S3_PUBLIC_ENDPOINT_URL
        if public_endpoint_url is None:
            return self.client
        return s3_client(self.settings, public_endpoint_url)

    def _normalize_mime_type(
        self, filename: str, content_type: str | None = None
    ) -> str:
        if content_type:
            return content_type
        guessed_type, _ = mimetypes.guess_type(filename)
        return guessed_type or "application/octet-stream"

    def compute_sha256(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def max_upload_size_bytes(self, kind: UploadKind) -> int:
        if kind is UploadKind.IMAGE:
            return self.settings.STORAGE_IMAGE_MAX_SIZE_BYTES
        if kind is UploadKind.PDF:
            return self.settings.STORAGE_PDF_MAX_SIZE_BYTES
        if kind is UploadKind.VIDEO:
            return self.settings.STORAGE_VIDEO_MAX_SIZE_BYTES
        return self.settings.STORAGE_FILE_MAX_SIZE_BYTES

    async def read_upload(
        self,
        upload: UploadStream,
        *,
        content_length: int | None,
        kind: UploadKind,
        error_context: str,
    ) -> bytes:
        max_size_bytes = self.max_upload_size_bytes(kind)
        if content_length is not None and content_length > max_size_bytes:
            raise StorageFileTooLarge(f"{error_context}:size:{content_length}")
        chunks: list[bytes] = []
        size = 0
        while chunk := await upload.read(UPLOAD_CHUNK_SIZE_BYTES):
            size += len(chunk)
            if size > max_size_bytes:
                raise StorageFileTooLarge(f"{error_context}:size:{size}")
            chunks.append(chunk)
        return b"".join(chunks)

    def validate_file(
        self,
        filename: str,
        content: bytes,
        content_type: str | None,
        *,
        max_size_bytes: int,
        error_context: str,
        allowed_mime_types: set[str] | None = None,
        mime_prefix: str | None = None,
    ) -> str:
        sniffed_mime_type = sniff_mime_type(content)
        restricted = allowed_mime_types is not None or mime_prefix is not None
        if sniffed_mime_type is None and restricted:
            raise StorageFileInvalidMimeType(f"{error_context}:signature")
        mime_type = sniffed_mime_type or self._normalize_mime_type(
            filename, content_type
        )
        if allowed_mime_types is not None and mime_type not in allowed_mime_types:
            raise StorageFileInvalidMimeType(f"{error_context}:mime:{mime_type}")
        if mime_prefix is not None and not mime_type.startswith(mime_prefix):
            raise StorageFileInvalidMimeType(f"{error_context}:mime:{mime_type}")
        if len(content) > max_size_bytes:
            raise StorageFileTooLarge(f"{error_context}:size:{len(content)}")
        return mime_type

    def validate_image_file(
        self,
        filename: str,
        content: bytes,
        content_type: str | None,
        *,
        error_context: str,
        allowed_mime_types: set[str] | None = None,
    ) -> str:
        return self.validate_file(
            filename,
            content,
            content_type,
            max_size_bytes=self.max_upload_size_bytes(UploadKind.IMAGE),
            error_context=error_context,
            allowed_mime_types=allowed_mime_types,
            mime_prefix="image/" if allowed_mime_types is None else None,
        )

    def validate_image_or_pdf_file(
        self,
        filename: str,
        content: bytes,
        content_type: str | None,
        *,
        error_context: str,
    ) -> str:
        return self.validate_file(
            filename,
            content,
            content_type,
            max_size_bytes=self.max_upload_size_bytes(UploadKind.PDF),
            error_context=error_context,
            allowed_mime_types=IMAGE_OR_PDF_MIME_TYPES,
        )

    def validate_pdf_file(
        self,
        filename: str,
        content: bytes,
        content_type: str | None,
        *,
        error_context: str,
    ) -> str:
        return self.validate_file(
            filename,
            content,
            content_type,
            max_size_bytes=self.max_upload_size_bytes(UploadKind.PDF),
            error_context=error_context,
            allowed_mime_types={"application/pdf"},
        )

    def validate_video_file(
        self,
        filename: str,
        content: bytes,
        content_type: str | None,
        *,
        error_context: str,
    ) -> str:
        return self.validate_file(
            filename,
            content,
            content_type,
            max_size_bytes=self.max_upload_size_bytes(UploadKind.VIDEO),
            error_context=error_context,
            mime_prefix="video/",
        )

    def validate_generic_file(
        self,
        filename: str,
        content: bytes,
        content_type: str | None,
        *,
        error_context: str,
    ) -> str:
        return self.validate_file(
            filename,
            content,
            content_type,
            max_size_bytes=self.max_upload_size_bytes(UploadKind.FILE),
            error_context=error_context,
        )

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
                self.presign_client.generate_presigned_url(
                    "get_object",
                    Params={
                        "Bucket": self.settings.SIP_S3_FILES_BUCKET,
                        "Key": key,
                        "ResponseContentDisposition": content_disposition_attachment(
                            filename
                        ),
                    },
                    ExpiresIn=self.settings.S3_PRESIGN_EXPIRY_SECONDS,
                ),
            )

        return await asyncio.to_thread(_presign)
