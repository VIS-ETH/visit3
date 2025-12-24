from fastapi import FastAPI
from app.api.router import router as api_router
from app.db.db import create_db_and_tables
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.include_router(api_router)

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    await create_db_and_tables()
