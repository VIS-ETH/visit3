from typing import cast

from starlette.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.main import app


def _cors_origins() -> list[str]:
    for middleware in app.user_middleware:
        if middleware.cls is CORSMiddleware:
            return cast(list[str], middleware.kwargs["allow_origins"])
    raise AssertionError("CORS middleware is not configured")


def test_cors_allows_only_the_frontend_origin():
    assert _cors_origins() == [get_settings().VISIT_FRONTEND_SERVER_URL]
