import hashlib
import json
from dataclasses import dataclass
from unittest.mock import MagicMock

import phonenumbers
import pytest
from pydantic import BaseModel

from app.core.utils import (
    dump_json,
    hash_str,
    load_json,
    normalize_email,
    normalize_phone_number,
    strip_text,
)


def test_normalize_email_strips_and_lowercases():
    assert normalize_email("  HeLLo@Example.COM  ") == "hello@example.com"
    assert normalize_email("user@domain.com") == "user@domain.com"


@pytest.mark.parametrize(
    "phone_number,expected",
    [
        ("079 123 45 67", "+41791234567"),
        ("+41 79 123 45 67", "+41791234567"),
        ("  044 123 45 67  ", "+41441234567"),
    ],
)
def test_normalize_phone_number_parses_swiss_numbers(phone_number, expected):
    assert normalize_phone_number(phone_number) == expected


def test_normalize_phone_number_returns_none_for_empty():
    assert normalize_phone_number(None) is None
    assert normalize_phone_number("") is None
    assert normalize_phone_number("   ") is None


def test_normalize_phone_number_rejects_invalid_number():
    with pytest.raises(phonenumbers.NumberParseException):
        normalize_phone_number("not-a-phone")
    with pytest.raises(ValueError):
        normalize_phone_number("123")


def test_strip_text_trims_or_returns_none():
    assert strip_text("  hello  ") == "hello"
    assert strip_text(None) is None
    assert strip_text("") == ""
    assert strip_text("x") == "x"


def test_hash_str_returns_sha256_hex():
    value = "some-token"
    assert hash_str(value) == hashlib.sha256(value.encode()).hexdigest()


def test_dump_json_serializes_pydantic_models():
    class Item(BaseModel):
        name: str
        count: int

    payload = {"items": [Item(name="a", count=1), Item(name="b", count=2)]}
    result = dump_json(payload)

    assert json.loads(result) == {
        "items": [{"name": "a", "count": 1}, {"name": "b", "count": 2}]
    }


def test_dump_json_fails_on_non_serializable_object():
    @dataclass
    class NotSerializable:
        value: int

    with pytest.raises(TypeError):
        dump_json({"item": NotSerializable(value=1)})


def test_load_json_validates_pydantic_model():
    class Item(BaseModel):
        name: str
        count: int

    result = load_json(Item, '{"name": "a", "count": 1}')

    assert isinstance(result, Item)
    assert result.name == "a"
    assert result.count == 1


def test_load_json_rejects_non_model_type():
    with pytest.raises(TypeError):
        load_json(dict, '{"key": "value"}')


def test_load_json_uses_model_validate_on_mock_type():
    target = MagicMock()
    target.model_validate.return_value = {"validated": True}

    result = load_json(target, '{"any": "thing"}')

    target.model_validate.assert_called_once_with({"any": "thing"})
    assert result == {"validated": True}
