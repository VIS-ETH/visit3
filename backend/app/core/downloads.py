import re
import unicodedata
from urllib.parse import quote

SAFE_FILENAME_CHARS = {" ", ".", "-", "_", "(", ")"}
CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]+")
SEPARATOR_CHARS_RE = re.compile(r"[\\/]+")
REPEATED_DASH_RE = re.compile(r"-{2,}")


def sanitize_download_filename(filename: str, default: str = "download") -> str:
    value = CONTROL_CHARS_RE.sub("", filename).strip()
    value = SEPARATOR_CHARS_RE.sub("-", value)
    safe = "".join(
        character if character.isalnum() or character in SAFE_FILENAME_CHARS else "-"
        for character in value
    )
    safe = REPEATED_DASH_RE.sub("-", safe).strip(" .-")
    return safe or default


def ascii_download_filename(filename: str, default: str = "download") -> str:
    normalized = unicodedata.normalize("NFKD", filename)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    return sanitize_download_filename(ascii_value, default)


def content_disposition_attachment(filename: str) -> str:
    safe_filename = sanitize_download_filename(filename)
    ascii_filename = ascii_download_filename(safe_filename)
    encoded_filename = quote(safe_filename, safe="")
    return (
        f'attachment; filename="{ascii_filename}"; '
        f"filename*=UTF-8''{encoded_filename}"
    )
