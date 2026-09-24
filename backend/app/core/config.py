from functools import lru_cache
from typing import Any

from pydantic import model_validator
from pydantic_settings import BaseSettings

EXAMPLE_SECRET_KEY = "5fcfacda13cd6e44e358f1109094a82d3319dd3631f2def507e5af4b4679a65c"
MIN_SECRET_KEY_LENGTH = 32


class WeakSecretKey(RuntimeError):
    def __init__(self) -> None:
        super().__init__(
            "SECRET_KEY must be a unique random value of at least "
            f"{MIN_SECRET_KEY_LENGTH} characters when DEBUG is disabled. "
            "For a local dev stack set DEBUG=true in backend/.env. Otherwise put "
            "a fresh key from `openssl rand -hex 32` into SECRET_KEY and never "
            "reuse the value from backend/.env.example."
        )


class Settings(BaseSettings):
    @classmethod
    def from_environment(cls) -> "Settings":
        no_explicit_overrides: dict[str, Any] = {}
        return cls(**no_explicit_overrides)

    SIP_POSTGRES_DB_SERVER: str
    SIP_POSTGRES_DB_NAME: str
    SIP_POSTGRES_DB_PORT: str
    SIP_POSTGRES_DB_USER: str
    SIP_POSTGRES_DB_PW: str

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.SIP_POSTGRES_DB_USER}:{self.SIP_POSTGRES_DB_PW}"
            f"@{self.SIP_POSTGRES_DB_SERVER}:{self.SIP_POSTGRES_DB_PORT}/{self.SIP_POSTGRES_DB_NAME}"
        )

    SECRET_KEY: str
    NOTIFICATION_API_URL: str
    NOTIFICATION_API_TLS: bool = False
    NOTIFICATION_API_CA_FILE: str | None = None
    VISIT_FRONTEND_SERVER_URL: str
    DEFAULT_NOTIFICATION_EMAIL: str = "kontaktparty@vis.ethz.ch"
    SIP_AUTH_OIDC_ISSUER: str
    SIP_AUTH_OIDC_CLIENT_ID: str
    KEYCLOAK_CALLBACK: str
    SIP_AUTH_OIDC_CLIENT_SECRET: str
    SIP_AUTH_OIDC_TOKEN_ENDPOINT: str
    SIP_AUTH_OIDC_AUTH_ENDPOINT: str
    SIP_AUTH_OIDC_JWKS_URL: str
    KEYCLOAK_ALGORITHM: str
    ADMIN_GROUP: str
    VISIT_KP_PRESIDENT_ROLE: str
    SIP_S3_FILES_HOST: str
    SIP_S3_FILES_PORT: str
    SIP_S3_FILES_USE_SSL: bool = True
    SIP_S3_FILES_ACCESS_KEY: str
    SIP_S3_FILES_SECRET_KEY: str
    SIP_S3_FILES_BUCKET: str
    S3_REGION: str = "us-east-1"
    S3_PUBLIC_ENDPOINT_URL: str | None = None
    S3_PRESIGN_EXPIRY_SECONDS: int = 3600
    STORAGE_FILE_MAX_SIZE_BYTES: int = 25 * 1024 * 1024
    STORAGE_IMAGE_MAX_SIZE_BYTES: int = 10 * 1024 * 1024
    STORAGE_VIDEO_MAX_SIZE_BYTES: int = 100 * 1024 * 1024
    STORAGE_PDF_MAX_SIZE_BYTES: int = 25 * 1024 * 1024
    STORAGE_ORPHAN_CLEANUP_MAX_AGE_HOURS: int = 24
    RATE_LIMIT_MAX_REQUESTS: int = 5
    RATE_LIMIT_WINDOW_SECONDS: int = 900
    RATE_LIMIT_TRUSTED_PROXIES: list[str] = []
    DEBUG_KEYCLOAK_ADMIN: bool = False
    DEBUG: bool = False

    @property
    def S3_ENDPOINT_URL(self) -> str:
        scheme = "https" if self.SIP_S3_FILES_USE_SSL else "http"
        return f"{scheme}://{self.SIP_S3_FILES_HOST}:{self.SIP_S3_FILES_PORT}"

    @model_validator(mode="after")
    def reject_weak_secret_key(self) -> "Settings":
        if self.DEBUG:
            return self
        if (
            self.SECRET_KEY == EXAMPLE_SECRET_KEY
            or len(self.SECRET_KEY) < MIN_SECRET_KEY_LENGTH
        ):
            raise WeakSecretKey()
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings.from_environment()
