from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app import storage
from app.schemas import TaskCreate

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


@router.post("/tasks", status_code=201)
def create_task(payload: TaskCreate):
    if not payload.title:
        return JSONResponse(
            status_code=400,
            content={"error": "title is required"},
        )
    return storage.create_task(payload.title)
