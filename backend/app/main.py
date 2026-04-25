import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_csrf_protect import CsrfProtect
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.deps import SessionLocal
from app.core.exceptions import AppError
from app.core.grpc import grpc_client
from app.core.scheduler import Scheduler
from app.repositories.kp_repository import KpRepository
from app.repositories.token_repository import TokenRepository
from app.routes.router import router as api_router
from app.services.storage_service import StorageService

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


async def cleanup_orphaned_stored_files():
    async with SessionLocal() as session:
        settings = get_settings()
        storage_service = StorageService(settings)
        kp_repository = KpRepository(session)
        orphaned_files = await kp_repository.list_orphaned_stored_files(
            settings.STORAGE_ORPHAN_CLEANUP_MAX_AGE_HOURS
        )
        for stored_file in orphaned_files:
            await storage_service.delete_object(stored_file.storage_key)
            await kp_repository.delete_stored_file(stored_file)


scheduler = Scheduler()
scheduler.add(cleanup_expired_tokens, interval=3600)
scheduler.add(cleanup_orphaned_stored_files, interval=3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await grpc_client.connect(get_settings().NOTIFICATION_API_URL)
    await scheduler.start()

    yield

    await scheduler.stop()
    await grpc_client.disconnect()


app = FastAPI(lifespan=lifespan)


def _validation_error_code(error: dict) -> str:
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


def _validation_error_field(error: dict) -> str:
    loc = error.get("loc", ())
    field_parts = [str(part) for part in loc if part not in {"body", "query", "path"}]
    return ".".join(field_parts)


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


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request, exc: RequestValidationError
):
    field_errors = [
        {
            "field": _validation_error_field(error),
            "code": _validation_error_code(error),
            "message": error.get("msg", "Invalid input"),
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
