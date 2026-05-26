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
from app.services.storage_service import StorageService


def make_storage_service(client=None) -> StorageService:
    service = StorageService.__new__(StorageService)
    service.settings = get_settings()
    service.client = client or Mock()
    return service


def test_validate_image_file_accepts_known_image_type():
    service = make_storage_service()

    mime_type = service.validate_image_file(
        "logo.png",
        b"\x89PNG\r\n",
        "image/png",
        error_context="logo",
    )

    assert mime_type == "image/png"


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
