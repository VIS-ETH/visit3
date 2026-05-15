import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_csrf_protect import CsrfProtect
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.exception_handlers import register_exception_handlers
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
    httponly: bool = False


@CsrfProtect.load_config  # type: ignore
def get_csrf_config():
    return CsrfSettings()


app = FastAPI(lifespan=lifespan)
register_exception_handlers(app)


origins = [
    get_settings().VISIT_FRONTEND_SERVER_URL,
    get_settings().SIP_AUTH_OIDC_ISSUER,
]

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
