from fastapi import FastAPI
from app.api.router import router as api_router
from app.db.db import create_db_and_tables
from app.deps import get_engine, get_settings

app = FastAPI()

app.include_router(api_router)

@app.on_event("startup")
def on_startup():
    settings = get_settings()
    engine = get_engine(settings)
    create_db_and_tables(engine)