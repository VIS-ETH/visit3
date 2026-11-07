import hashlib
import re
import unicodedata
from pathlib import Path
from typing import overload

import phonenumbers
from pydantic import HttpUrl, TypeAdapter, ValidationError

_http_url = TypeAdapter(HttpUrl)

CONTROL_CHARACTER_CATEGORY = "Cc"


def has_control_characters(value: str) -> bool:
    return any(
        unicodedata.category(character) == CONTROL_CHARACTER_CATEGORY
        for character in value
    )


INVISIBLE_LETTERS = frozenset({"\u115f", "\u1160", "\u2800", "\u3164", "\uffa0"})


def reject_control_characters(value: str) -> str:
    if has_control_characters(value):
        raise ValueError("control characters are not allowed")
    return value


def clean_name(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    if any(unicodedata.category(character) in ("Cc", "Cf") for character in value):
        raise ValueError("control or formatting characters are not allowed")
    if value and all(
        character.isspace() or character in INVISIBLE_LETTERS for character in value
    ):
        raise ValueError("name must contain visible characters")
    return value


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_phone_number(phone_number: str | None) -> str | None:
    if phone_number is None:
        return None
    stripped = phone_number.strip()
    if not stripped:
        return None
    parsed = phonenumbers.parse(stripped, "CH")
    if not phonenumbers.is_valid_number(parsed):
        raise ValueError("invalid phone number")
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


@overload
def strip_text(value: str) -> str: ...


@overload
def strip_text(value: None) -> None: ...


def strip_text(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip()


def normalize_http_url(url: str | None) -> str | None:
    stripped = strip_text(url)
    if not stripped:
        return None
    try:
        _http_url.validate_python(stripped)
    except ValidationError as error:
        raise ValueError("url must start with http:// or https://") from error
    return stripped


def hash_str(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


MAX_FILENAME_LENGTH = 255
_SAFE_SUFFIX = re.compile(r"\.[A-Za-z0-9]{1,10}")


def safe_suffix(filename: str) -> str:
    suffix = Path(filename).suffix
    return suffix.lower() if _SAFE_SUFFIX.fullmatch(suffix) else ""


def bounded_filename(filename: str) -> str:
    return filename[-MAX_FILENAME_LENGTH:]
