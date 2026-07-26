from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/",
    summary="API info",
    description="Return the API name, version, and available endpoints.",
)
def root():
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@router.get(
    "/health",
    summary="Health check",
    description="Return a simple status payload to confirm the server is running.",
)
def health():
    return {"status": "ok"}
