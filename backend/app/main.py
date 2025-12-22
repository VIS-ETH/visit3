from fastapi import FastAPI
from app.api.router import router as api_router
from app.db.db import create_db_and_tables

app = FastAPI()

app.include_router(api_router)


@app.on_event("startup")
async def on_startup():
    await create_db_and_tables()
