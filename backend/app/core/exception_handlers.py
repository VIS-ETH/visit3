import logging
from typing import TypeGuard

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.exceptions import AppError, ConcurrentChange
from app.core.request_id import current_request_id

logger = logging.getLogger(__name__)


class UnexpectedErrorMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        response_started = False

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, tracking_send)
        except Exception:
            request_id = current_request_id()
            logger.exception(
                "Unhandled error on %s %s (request %s)",
                scope["method"],
                scope["path"],
                request_id,
            )
            if response_started:
                raise
            response = JSONResponse(
                status_code=500,
                content={
                    "statusCode": 500,
                    "code": "error.internal",
                    "identifier": "unhandled",
                    "message": "Internal server error",
                    "requestId": request_id,
                },
            )
            await response(scope, receive, send)


def register_exception_handlers(app: FastAPI) -> None:
    app.exception_handler(AppError)(app_error_handler)
    app.exception_handler(RequestValidationError)(request_validation_error_handler)
    app.exception_handler(IntegrityError)(integrity_error_handler)


async def integrity_error_handler(
    request: Request, exc: IntegrityError
) -> JSONResponse:
    logger.warning(
        "Concurrent change on %s %s (request %s)",
        request.method,
        request.url.path,
        current_request_id(),
    )
    return await app_error_handler(
        request, ConcurrentChange(f"integrity:{request.method}:{request.url.path}")
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    content: dict[str, object] = {
        "statusCode": exc.status_code,
        "code": exc.code,
        "identifier": exc.identifier,
        "message": exc.message,
    }
    if exc.details is not None:
        content["details"] = exc.details
    if exc.status_code >= 500:
        request_id = current_request_id()
        logger.error(
            "Server error %s on %s %s (request %s): %s",
            exc.code,
            request.method,
            request.url.path,
            request_id,
            exc.identifier,
            exc_info=exc,
        )
        content["requestId"] = request_id
    return JSONResponse(status_code=exc.status_code, content=content)


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
    if "url" in error_type or "url" in message:
        return "validation.invalid_url"
    if error_type in {"uuid_parsing", "uuid_type"}:
        return "validation.invalid_uuid"
    if error_type in {"int_parsing", "int_type"}:
        return "validation.invalid_integer"
    if error_type in {"float_parsing", "float_type"} or error_type.startswith(
        "decimal_"
    ):
        return "validation.invalid_number"
    if error_type in {
        "greater_than",
        "greater_than_equal",
        "less_than",
        "less_than_equal",
    }:
        return "validation.out_of_range"
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
