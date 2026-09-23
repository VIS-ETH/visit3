import hashlib
from io import BytesIO
from unittest.mock import Mock

import pytest
from botocore.exceptions import ClientError

from app.core.config import get_settings
from app.core.exceptions import (
    StorageDownloadFailed,
    StorageFileInvalidMimeType,
    StorageFileTooLarge,
    StorageUploadFailed,
)
from app.services.storage_service import StorageService, UploadKind, sniff_mime_type


def make_storage_service(client=None, **settings_overrides) -> StorageService:
    service = StorageService.__new__(StorageService)
    service.settings = get_settings().model_copy(update=settings_overrides)
    service.client = client or Mock()
    return service


class CountingUpload:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.offset = 0
        self.read_calls = 0

    async def read(self, size: int = -1) -> bytes:
        self.read_calls += 1
        end = len(self.content) if size < 0 else self.offset + size
        chunk = self.content[self.offset : end]
        self.offset += len(chunk)
        return chunk


async def test_read_upload_rejects_content_length_over_limit_before_reading():
    service = make_storage_service(STORAGE_IMAGE_MAX_SIZE_BYTES=1024)
    upload = CountingUpload(b"image-bytes")

    with pytest.raises(StorageFileTooLarge):
        await service.read_upload(
            upload,
            content_length=1025,
            kind=UploadKind.IMAGE,
            error_context="service_image",
        )

    assert upload.read_calls == 0


async def test_read_upload_aborts_stream_once_limit_is_exceeded():
    service = make_storage_service(STORAGE_IMAGE_MAX_SIZE_BYTES=1024 * 1024)
    upload = CountingUpload(b"\x00" * (5 * 1024 * 1024))

    with pytest.raises(StorageFileTooLarge):
        await service.read_upload(
            upload,
            content_length=None,
            kind=UploadKind.IMAGE,
            error_context="service_image",
        )

    assert upload.read_calls == 2
    assert upload.offset < len(upload.content)


async def test_read_upload_returns_content_within_limit():
    service = make_storage_service()
    upload = CountingUpload(b"small image")

    content = await service.read_upload(
        upload,
        content_length=len(b"small image"),
        kind=UploadKind.IMAGE,
        error_context="service_image",
    )

    assert content == b"small image"


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 16
GIF_BYTES = b"GIF89a" + b"\x00" * 16
WEBP_BYTES = b"RIFF\x24\x00\x00\x00WEBPVP8 "
PDF_BYTES = b"%PDF-1.7\n1 0 obj\n"
MP4_BYTES = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 16
QUICKTIME_BYTES = b"\x00\x00\x00\x14ftypqt  " + b"\x00" * 16
WEBM_BYTES = b"\x1a\x45\xdf\xa3" + b"\x00" * 16
HEIC_BYTES = b"\x00\x00\x00\x18ftypheic" + b"\x00" * 16
HEIX_BYTES = b"\x00\x00\x00\x18ftypheix" + b"\x00" * 16
HEIF_BYTES = b"\x00\x00\x00\x18ftypmif1" + b"\x00" * 16
AVIF_BYTES = b"\x00\x00\x00\x18ftypavif" + b"\x00" * 16
HTML_BYTES = b"<!DOCTYPE html><html><body>hi</body></html>"
UNKNOWN_BYTES = b"\x01\x02\x03\x04\x05\x06\x07\x08"


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (PNG_BYTES, "image/png"),
        (JPEG_BYTES, "image/jpeg"),
        (GIF_BYTES, "image/gif"),
        (WEBP_BYTES, "image/webp"),
        (PDF_BYTES, "application/pdf"),
        (MP4_BYTES, "video/mp4"),
        (QUICKTIME_BYTES, "video/quicktime"),
        (HEIC_BYTES, "image/heic"),
        (HEIX_BYTES, "image/heic"),
        (HEIF_BYTES, "image/heic"),
        (AVIF_BYTES, "image/avif"),
        (WEBM_BYTES, "video/webm"),
        (HTML_BYTES, None),
        (UNKNOWN_BYTES, None),
        (b"", None),
    ],
)
def test_sniff_mime_type_matches_known_signatures(content: bytes, expected: str | None):
    assert sniff_mime_type(content) == expected


def test_validate_image_file_accepts_known_image_type():
    service = make_storage_service()

    mime_type = service.validate_image_file(
        "logo.png",
        PNG_BYTES,
        "image/png",
        error_context="logo",
    )

    assert mime_type == "image/png"


def test_validate_image_file_rejects_html_declared_as_png():
    service = make_storage_service()

    with pytest.raises(StorageFileInvalidMimeType):
        service.validate_image_file(
            "logo.png",
            HTML_BYTES,
            "image/png",
            error_context="logo",
        )


def test_validate_image_file_stores_sniffed_mime_type_over_declared_one():
    service = make_storage_service()

    mime_type = service.validate_image_file(
        "logo.bin",
        PNG_BYTES,
        "application/octet-stream",
        error_context="logo",
    )

    assert mime_type == "image/png"


def test_validate_image_file_rejects_unknown_bytes():
    service = make_storage_service()

    with pytest.raises(StorageFileInvalidMimeType):
        service.validate_image_file(
            "logo.png",
            UNKNOWN_BYTES,
            "image/png",
            error_context="logo",
        )


def test_validate_pdf_file_accepts_pdf_signature():
    service = make_storage_service()

    mime_type = service.validate_pdf_file(
        "document.pdf",
        PDF_BYTES,
        "application/octet-stream",
        error_context="document",
    )

    assert mime_type == "application/pdf"


def test_validate_video_file_accepts_mp4_signature():
    service = make_storage_service()

    mime_type = service.validate_video_file(
        "clip.mp4",
        MP4_BYTES,
        "video/quicktime",
        error_context="clip",
    )

    assert mime_type == "video/mp4"


def test_validate_image_file_rejects_pdf_bytes_for_nametag_background():
    service = make_storage_service()

    with pytest.raises(StorageFileInvalidMimeType):
        service.validate_image_file(
            "background.png",
            PDF_BYTES,
            "image/png",
            error_context="nametag_background",
            allowed_mime_types={"image/png", "image/jpeg"},
        )


def test_validate_generic_file_falls_back_to_declared_type():
    service = make_storage_service()

    mime_type = service.validate_generic_file(
        "notes.txt",
        b"plain notes",
        "text/plain",
        error_context="notes",
    )

    assert mime_type == "text/plain"


def test_validate_file_rejects_wrong_mime_type():
    service = make_storage_service()

    with pytest.raises(StorageFileInvalidMimeType):
        service.validate_pdf_file(
            "not-a-pdf.txt",
            b"text",
            "text/plain",
            error_context="document",
        )


def test_validate_file_rejects_oversized_content():
    service = make_storage_service()

    with pytest.raises(StorageFileTooLarge):
        service.validate_file(
            "large.bin",
            b"too large",
            "application/octet-stream",
            max_size_bytes=3,
            error_context="upload",
        )


async def test_upload_bytes_stores_object_and_returns_metadata():
    client = Mock()
    client.put_object.return_value = {"ETag": '"etag-123"'}
    service = make_storage_service(client)

    result = await service.upload_bytes(
        "files/report.txt",
        b"content",
        "report.txt",
        "text/plain",
    )

    client.put_object.assert_called_once_with(
        Bucket=service.settings.SIP_S3_FILES_BUCKET,
        Key="files/report.txt",
        Body=b"content",
        ContentType="text/plain",
    )
    assert result.key == "files/report.txt"
    assert result.etag == "etag-123"
    assert result.mime_type == "text/plain"
    assert result.size_bytes == len(b"content")
    assert result.sha256 == hashlib.sha256(b"content").hexdigest()


async def test_upload_bytes_wraps_client_errors():
    client = Mock()
    client.put_object.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "nope"}},
        "PutObject",
    )
    service = make_storage_service(client)

    with pytest.raises(StorageUploadFailed):
        await service.upload_bytes("files/report.txt", b"content", "report.txt")


async def test_download_bytes_reads_response_body():
    client = Mock()
    client.get_object.return_value = {"Body": BytesIO(b"downloaded")}
    service = make_storage_service(client)

    content = await service.download_bytes("files/report.txt")

    assert content == b"downloaded"
    client.get_object.assert_called_once_with(
        Bucket=service.settings.SIP_S3_FILES_BUCKET,
        Key="files/report.txt",
    )


async def test_download_bytes_wraps_client_errors():
    client = Mock()
    client.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "missing"}},
        "GetObject",
    )
    service = make_storage_service(client)

    with pytest.raises(StorageDownloadFailed):
        await service.download_bytes("missing.txt")


async def test_generate_download_url_sanitizes_content_disposition_filename():
    client = Mock()
    client.generate_presigned_url.return_value = "https://files.example/download"
    service = make_storage_service(client)

    url = await service.generate_download_url("files/report.pdf", 'Käpp/"report\r.pdf')

    assert url == "https://files.example/download"
    params = client.generate_presigned_url.call_args.kwargs["Params"]
    assert params["Key"] == "files/report.pdf"
    disposition = params["ResponseContentDisposition"]
    assert 'filename="Kapp-report.pdf"' in disposition
    assert "filename*=UTF-8''K%C3%A4pp-report.pdf" in disposition
    assert "\r" not in disposition
    assert "/" not in disposition


def test_validate_image_file_rejects_heic_with_its_sniffed_mime_type():
    service = make_storage_service()

    with pytest.raises(StorageFileInvalidMimeType) as error:
        service.validate_image_file(
            "photo.heic",
            HEIC_BYTES,
            "image/png",
            error_context="requirement_file",
            allowed_mime_types={"image/png", "image/jpeg"},
        )

    assert error.value.identifier.endswith("mime:image/heic")
