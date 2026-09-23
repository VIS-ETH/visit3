from fastapi import Request, UploadFile


def content_length(request: Request) -> int | None:
    header = request.headers.get("content-length")
    return int(header) if header is not None and header.isdigit() else None


def upload_size(request: Request, file: UploadFile) -> int | None:
    return file.size if file.size is not None else content_length(request)
