from typing import TypeGuard

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import AppError


def register_exception_handlers(app: FastAPI) -> None:
    app.exception_handler(AppError)(app_error_handler)
    app.exception_handler(RequestValidationError)(request_validation_error_handler)


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "statusCode": exc.status_code,
            "code": exc.code,
            "identifier": exc.identifier,
            "message": exc.message,
        },
    )


async def request_validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    field_errors: list[dict[str, str]] = [
        {
            "field": _validation_error_field(error),
            "code": _validation_error_code(error),
            "message": str(error.get("msg", "Invalid input")),
        }
        for error in exc.errors()
    ]
    first_error_code = (
        field_errors[0]["code"] if field_errors else "error.validation_failed"
    )
    return JSONResponse(
        status_code=422,
        content={
            "statusCode": 422,
            "code": "error.validation_failed",
            "detail": first_error_code,
            "fieldErrors": field_errors,
            "message": "Request validation failed",
        },
    )


def _validation_error_code(error: dict[str, object]) -> str:
    error_type = str(error.get("type", ""))
    message = str(error.get("msg", "")).lower()

    if error_type == "missing":
        return "validation.required"
    if "email" in error_type or "email" in message:
        return "validation.invalid_email"
    if error_type in {"uuid_parsing", "uuid_type"}:
        return "validation.invalid_uuid"
    if error_type in {"int_parsing", "int_type"}:
        return "validation.invalid_integer"
    if error_type in {"float_parsing", "float_type", "decimal_parsing"}:
        return "validation.invalid_number"
    if error_type in {"bool_parsing", "bool_type"}:
        return "validation.invalid_boolean"
    if error_type in {"date_parsing", "date_type", "datetime_parsing", "datetime_type"}:
        return "validation.invalid_date"
    if error_type in {"string_type", "string_pattern_mismatch"}:
        return "validation.invalid_string"
    if error_type == "string_too_short":
        return "validation.too_short"
    if error_type == "string_too_long":
        return "validation.too_long"
    return "validation.invalid"


def _is_validation_loc(value: object) -> TypeGuard[tuple[object, ...] | list[object]]:
    return isinstance(value, (tuple, list))


def _validation_error_field(error: dict[str, object]) -> str:
    loc = error.get("loc", ())
    if not _is_validation_loc(loc):
        return ""
    field_parts = [str(part) for part in loc if part not in {"body", "query", "path"}]
    return ".".join(field_parts)
