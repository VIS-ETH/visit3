from contextlib import asynccontextmanager
import logging
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.core.exceptions import AppError
from app.routes.router import router as api_router
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.scheduler import Scheduler
from fastapi_csrf_protect import CsrfProtect
from app.core.grpc import grpc_client
from app.core.deps import SessionLocal
from app.repositories.token_repository import TokenRepository


LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(levelname)s:%(name)s:%(message)s",
    force=True,
)


class CsrfSettings(BaseModel):
    secret_key: str = get_settings().SECRET_KEY
    httponly: bool = False


@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()


async def cleanup_expired_tokens():
    async with SessionLocal() as session:
        await TokenRepository(session).cleanup_expired()


scheduler = Scheduler()
scheduler.add(cleanup_expired_tokens, interval=3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await grpc_client.connect(get_settings().NOTIFICATION_API_URL)
    await scheduler.start()

    yield

    await scheduler.stop()
    await grpc_client.disconnect()


app = FastAPI(lifespan=lifespan)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "statusCode": exc.status_code,
            "code": exc.code,
            "identifier": exc.identifier,
            "message": exc.message,
        },
    )


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


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(api_router, prefix="/api")
