from collections.abc import Callable, Mapping
from functools import cached_property

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.request_id import current_request_id

DEFAULT_BODY_LIMIT_BYTES = 1024 * 1024
MULTIPART_OVERHEAD_BYTES = 64 * 1024
PAYLOAD_TOO_LARGE = 413


class RequestBodyTooLarge(HTTPException):
    def __init__(self, identifier: str) -> None:
        super().__init__(status_code=PAYLOAD_TOO_LARGE)
        self.identifier = identifier


def payload_too_large_response(identifier: str) -> JSONResponse:
    return JSONResponse(
        status_code=PAYLOAD_TOO_LARGE,
        content={
            "statusCode": PAYLOAD_TOO_LARGE,
            "code": "error.storage_file_too_large",
            "identifier": identifier,
            "message": "The request body is too large",
            "requestId": current_request_id(),
        },
    )


async def request_body_too_large_handler(
    _request: Request, exc: Exception
) -> JSONResponse:
    identifier = exc.identifier if isinstance(exc, RequestBodyTooLarge) else "body"
    return payload_too_large_response(identifier)


def _declared_length(scope: Scope) -> int | None:
    for name, value in scope.get("headers", ()):
        if name == b"content-length":
            return int(value) if value.isdigit() else None
    return None


class BodyLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        upload_limits: Callable[[], Mapping[Callable[..., object], int]],
        default_limit: int = DEFAULT_BODY_LIMIT_BYTES,
    ) -> None:
        self.app = app
        self.upload_limits = upload_limits
        self.default_limit = default_limit

    @cached_property
    def route_limits(self) -> dict[Callable[..., object], int]:
        return {
            endpoint: limit + MULTIPART_OVERHEAD_BYTES
            for endpoint, limit in self.upload_limits().items()
        }

    @cached_property
    def largest_limit(self) -> int:
        return max(self.default_limit, *self.route_limits.values())

    def _limit(self, scope: Scope) -> int:
        endpoint = scope.get("endpoint")
        if endpoint is None:
            return self.default_limit
        return self.route_limits.get(endpoint, self.default_limit)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = _declared_length(scope)
        if declared is not None and declared > self.largest_limit:
            identifier = f"body:{scope['method']}:{scope['path']}"
            await payload_too_large_response(identifier)(scope, receive, send)
            return
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            limit = self._limit(scope)
            identifier = f"body:{scope['method']}:{scope['path']}:{limit}"
            if declared is not None and declared > limit:
                raise RequestBodyTooLarge(identifier)
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise RequestBodyTooLarge(identifier)
            return message

        await self.app(scope, limited_receive, send)
