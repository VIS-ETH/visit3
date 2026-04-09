from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    SIP_POSTGRES_DB_SERVER: str
    SIP_POSTGRES_DB_NAME: str
    SIP_POSTGRES_DB_PORT: str
    SIP_POSTGRES_DB_USER: str
    SIP_POSTGRES_DB_PW: str

    @property
    def DATABASE_URL(self) -> str:
        return (
            f'postgresql+asyncpg://{self.SIP_POSTGRES_DB_USER}:{self.SIP_POSTGRES_DB_PW}'
            f'@{self.SIP_POSTGRES_DB_SERVER}:{self.SIP_POSTGRES_DB_PORT}/{self.SIP_POSTGRES_DB_NAME}'
        )

    SECRET_KEY: str
    NOTIFICATION_API_URL: str
    VISIT_FRONTEND_SERVER_URL: str
    KEYCLOAK_URL: str
    KEYCLOAK_CLIENT_ID: str
    KEYCLOAK_CALLBACK: str
    KEYCLOAK_CLIENT_SECRET: str
    KEYCLOAK_TOKEN_URL: str
    KEYCLOAK_AUTH_URL: str
    KEYCLOAK_JWKS_URL: str
    KEYCLOAK_ALGORITHM: str
    ADMIN_GROUP: str
    VISIT_KP_PRESIDENT_ROLE: str


@lru_cache
def get_settings():
    return Settings()
