from fastapi import FastAPI

from app.routers import meta

app = FastAPI()
app.include_router(meta.router)
