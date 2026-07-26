from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app import storage

router = APIRouter()


@router.get("/tasks")
def get_tasks():
    return storage.list_tasks()


@router.get("/tasks/{task_id}")
def get_task(task_id: int):
    task = storage.get_task(task_id)
    if task is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"},
        )
    return task
