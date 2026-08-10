from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import db
from app.routers import meta, tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once on startup, before the app accepts requests: ensures
    # tasks.db exists with the tasks table (and seed rows, if empty).
    db.init_db()
    yield


app = FastAPI(title="Task API", version="1.0", lifespan=lifespan)
app.include_router(meta.router)
app.include_router(tasks.router)
