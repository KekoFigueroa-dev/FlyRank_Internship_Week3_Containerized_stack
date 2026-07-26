from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@router.get("/health")
def health():
    return {"status": "ok"}
