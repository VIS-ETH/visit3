from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    GRPC_SERVER: str
    FRONTEND_SERVER: str
    KEYCLOAK_URL: str
    KEYCLOAK_CLIENT_ID: str
    KEYCLOAK_CALLBACK: str
    KEYCLOAK_CLIENT_SECRET: str
    KEYCLOAK_TOKEN_URL: str
    KEYCLOAK_AUTH_URL: str
    KEYCLOAK_JWKS_URL: str
    KEYCLOAK_ALGORITHM: str
    ADMIN_GROUP: str


@lru_cache
def get_settings():
    return Settings()
