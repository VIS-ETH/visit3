import logging
import os
from typing import Any, Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_csrf_protect import CsrfProtect
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.cookies import secure_cookies
from app.core.csrf import (
    CSRF_COOKIE_KEY,
    CSRF_COOKIE_PATH,
    CSRF_HEADER_NAME,
    CSRF_TOKEN_MAX_AGE,
)
from app.core.exception_handlers import (
    UnexpectedErrorMiddleware,
    register_exception_handlers,
)
from app.core.maintenance import lifespan
from app.routes.router import router as api_router

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(levelname)s:%(name)s:%(message)s",
    force=True,
)


class CsrfSettings(BaseModel):
    secret_key: str = get_settings().SECRET_KEY
    cookie_key: str = CSRF_COOKIE_KEY
    cookie_path: str = CSRF_COOKIE_PATH
    cookie_samesite: Literal["lax"] = "lax"
    cookie_secure: bool = Field(default_factory=secure_cookies)
    httponly: bool = True
    header_name: str = CSRF_HEADER_NAME
    max_age: int = CSRF_TOKEN_MAX_AGE


@CsrfProtect.load_config
def get_csrf_config() -> list[tuple[str, Any]]:
    return list(CsrfSettings())


app = FastAPI(lifespan=lifespan)
register_exception_handlers(app)


origins = [get_settings().VISIT_FRONTEND_SERVER_URL]

app.add_middleware(UnexpectedErrorMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/health" not in record.getMessage()


logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(api_router, prefix="/api")
