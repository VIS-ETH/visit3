from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
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
    VISIT_FRONTEND_SERVER_URL: str
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
    S3_PRESIGN_EXPIRY_SECONDS: int = 3600
    DEBUG_KEYCLOAK_ADMIN: bool = False
    DEBUG: bool = False

    @property
    def S3_ENDPOINT_URL(self) -> str:
        scheme = "https" if self.SIP_S3_FILES_USE_SSL else "http"
        return f"{scheme}://{self.SIP_S3_FILES_HOST}:{self.SIP_S3_FILES_PORT}"


@lru_cache
def get_settings():
    return Settings()
