from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import SQLModel
from app.api.router import router as api_router
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.deps import engine, grpc_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)

    await grpc_client.connect(settings.GRPC_SERVER)

    yield

    await grpc_client.disconnect()


app = FastAPI(lifespan=lifespan)

origins = [get_settings().FRONTEND_SERVER]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

