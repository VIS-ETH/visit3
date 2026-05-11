import hashlib
import json
from typing import Any, Protocol, TypeVar, cast, overload

import phonenumbers

T = TypeVar("T", covariant=True)


class ModelValidateType(Protocol[T]):
    @classmethod
    def model_validate(cls, obj: Any) -> T: ...


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


def hash_str(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def dump_json(value: Any) -> str:
    def _default_serializer(item: Any):
        if hasattr(item, "model_dump"):
            return item.model_dump()
        raise TypeError(
            f"Object of type {item.__class__.__name__} is not JSON serializable"
        )

    return json.dumps(value, default=_default_serializer)


def load_json(target_type: type[T], value: str) -> T:
    data = json.loads(value)

    if hasattr(target_type, "model_validate"):
        return cast(ModelValidateType[T], target_type).model_validate(data)
    else:
        raise TypeError(
            f"Target type {target_type.__name__} does not support model validation"
        )
