import hashlib
import json
from typing import Any, TypeVar

T = TypeVar("T")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_str(str) -> str:
    return hashlib.sha256(str.encode()).hexdigest()


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
        return target_type.model_validate(data)
    else:
        raise TypeError(
            f"Target type {target_type.__name__} does not support model validation"
        )
