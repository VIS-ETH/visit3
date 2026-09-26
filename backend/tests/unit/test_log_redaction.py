import logging

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.types import Receive, Scope, Send

from app.core.exception_handlers import UnexpectedErrorMiddleware
from app.core.log_redaction import AccessLogRedaction, redact_path
from app.main import HealthCheckFilter


def _access_record(path: str) -> logging.LogRecord:
    return logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("203.0.113.9:5000", "GET", path, "1.1", 200),
        None,
    )


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/api/auth/reset/abc123", "/api/auth/reset/[redacted]"),
        ("/api/auth/link/abc123", "/api/auth/link/[redacted]"),
        ("/api/user/confirm-email/abc123", "/api/user/confirm-email/[redacted]"),
        ("/api/company/invite/abc123", "/api/company/invite/[redacted]"),
        (
            "/api/company/invite/abc123/accept",
            "/api/company/invite/[redacted]/accept",
        ),
        (
            "/api/auth/callback?code=secret-code&state=secret-state",
            "/api/auth/callback?code=[redacted]&state=[redacted]",
        ),
        ("/api/company/invite", "/api/company/invite"),
        ("/api/company/me/profile", "/api/company/me/profile"),
    ],
)
def test_tokens_are_removed_from_paths(path: str, expected: str):
    assert redact_path(path) == expected


def test_the_access_log_hides_tokens_and_keeps_the_rest():
    record = _access_record("/api/auth/link/abc123?code=secret")

    assert AccessLogRedaction().filter(record) is True

    assert record.getMessage() == (
        '203.0.113.9:5000 - "GET /api/auth/link/[redacted]?code=[redacted] HTTP/1.1" 200'
    )


def test_unexpected_access_log_shapes_pass_through():
    record = logging.LogRecord(
        "uvicorn.access", logging.INFO, __file__, 1, "plain", None, None
    )

    assert AccessLogRedaction().filter(record) is True
    assert record.getMessage() == "plain"


def test_the_access_log_filters_are_installed():
    filters = logging.getLogger("uvicorn.access").filters

    assert {type(item) for item in filters} >= {HealthCheckFilter, AccessLogRedaction}


async def test_an_unexpected_error_logs_the_path_without_its_token(
    caplog: pytest.LogCaptureFixture,
):
    async def failing_app(scope: Scope, receive: Receive, send: Send) -> None:
        raise RuntimeError("boom")

    middleware = UnexpectedErrorMiddleware(failing_app)
    async with AsyncClient(
        transport=ASGITransport(app=middleware), base_url="https://test"
    ) as client:
        with caplog.at_level(logging.ERROR):
            response = await client.get("/api/auth/reset/secret-token")

    assert response.status_code == 500
    messages = "\n".join(record.getMessage() for record in caplog.records)
    assert "/api/auth/reset/[redacted]" in messages
    assert "secret-token" not in messages
