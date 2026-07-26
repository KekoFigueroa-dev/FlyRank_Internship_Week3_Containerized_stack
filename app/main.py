from fastapi import FastAPI

from app.routers import meta, tasks

app = FastAPI(title="Task API", version="1.0")
app.include_router(meta.router)
app.include_router(tasks.router)
