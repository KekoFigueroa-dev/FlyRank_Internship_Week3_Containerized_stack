from fastapi import FastAPI

from app.routers import meta, tasks

app = FastAPI()
app.include_router(meta.router)
app.include_router(tasks.router)
