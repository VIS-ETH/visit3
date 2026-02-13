from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from sqlmodel import SQLModel
from app.routers.router import router as api_router
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.deps import engine
from fastapi_csrf_protect import CsrfProtect
from app.core.grpc import grpc_client


class CsrfSettings(BaseModel):
    secret_key: str = get_settings().SECRET_KEY
    httponly: bool = False


@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await grpc_client.connect(get_settings().GRPC_SERVER)

    yield

    await grpc_client.disconnect()


app = FastAPI(lifespan=lifespan)

origins = [get_settings().FRONTEND_SERVER, get_settings().KEYCLOAK_URL]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
