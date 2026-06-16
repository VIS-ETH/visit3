from unittest.mock import MagicMock

import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError

from app.core.exception_handlers import (
    _validation_error_code,
    _validation_error_field,
    app_error_handler,
    register_exception_handlers,
    request_validation_error_handler,
)
from app.core.exceptions import AppError


def test_register_exception_handlers_attaches_handlers():
    app = MagicMock()
    register_exception_handlers(app)

    assert app.exception_handler.call_count == 2
    app.exception_handler.assert_any_call(AppError)
    app.exception_handler.assert_any_call(RequestValidationError)


@pytest.mark.asyncio
async def test_app_error_handler_returns_json_response():
    exc = AppError(
        status_code=403,
        code="error.forbidden",
        identifier="forbidden:test",
        message="Not allowed",
    )
    response = await app_error_handler(MagicMock(spec=Request), exc)

    assert response.status_code == 403
    assert response.body == b'{"statusCode":403,"code":"error.forbidden","identifier":"forbidden:test","message":"Not allowed"}'


@pytest.mark.asyncio
async def test_request_validation_error_handler_returns_field_errors():
    errors = [
        {
            "loc": ("body", "email"),
            "type": "value_error.email",
            "msg": "invalid email",
        },
        {
            "loc": ("body", "name"),
            "type": "missing",
            "msg": "field required",
        },
    ]
    exc = RequestValidationError(errors=errors)
    response = await request_validation_error_handler(MagicMock(spec=Request), exc)

    assert response.status_code == 422
    body = response.body.decode()
    assert '"code":"error.validation_failed"' in body
    assert '"field":"email"' in body
    assert '"code":"validation.invalid_email"' in body
    assert '"field":"name"' in body
    assert '"code":"validation.required"' in body


@pytest.mark.asyncio
async def test_request_validation_error_handler_uses_first_error_code_for_detail():
    errors = [
        {"loc": ("body", "x"), "type": "string_too_short", "msg": "too short"},
    ]
    exc = RequestValidationError(errors=errors)
    response = await request_validation_error_handler(MagicMock(spec=Request), exc)

    body = response.body.decode()
    assert '"detail":"validation.too_short"' in body


@pytest.mark.parametrize(
    "error,expected",
    [
        ({"type": "missing"}, "validation.required"),
        ({"type": "value_error.email", "msg": "Invalid email"}, "validation.invalid_email"),
        ({"type": "email", "msg": "not an email"}, "validation.invalid_email"),
        ({"type": "uuid_parsing"}, "validation.invalid_uuid"),
        ({"type": "uuid_type"}, "validation.invalid_uuid"),
        ({"type": "int_parsing"}, "validation.invalid_integer"),
        ({"type": "int_type"}, "validation.invalid_integer"),
        ({"type": "float_parsing"}, "validation.invalid_number"),
        ({"type": "decimal_parsing"}, "validation.invalid_number"),
        ({"type": "bool_parsing"}, "validation.invalid_boolean"),
        ({"type": "date_parsing"}, "validation.invalid_date"),
        ({"type": "datetime_type"}, "validation.invalid_date"),
        ({"type": "string_type"}, "validation.invalid_string"),
        ({"type": "string_pattern_mismatch"}, "validation.invalid_string"),
        ({"type": "string_too_short"}, "validation.too_short"),
        ({"type": "string_too_long"}, "validation.too_long"),
        ({"type": "custom"}, "validation.invalid"),
    ],
)
def test_validation_error_code_mapping(error, expected):
    assert _validation_error_code(error) == expected


@pytest.mark.parametrize(
    "error,expected",
    [
        ({"loc": ("body", "email")}, "email"),
        ({"loc": ("query", "page", 0)}, "page.0"),
        ({"loc": ("path", "id")}, "id"),
        ({"loc": ()}, ""),
        ({"loc": "not-a-loc"}, ""),
    ],
)
def test_validation_error_field_excludes_scope_parts(error, expected):
    assert _validation_error_field(error) == expected
