from fastapi import APIRouter, Response
from fastapi.responses import JSONResponse

from app import storage
from app.schemas import TaskCreate, TaskUpdate

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


@router.put("/tasks/{task_id}")
def update_task(task_id: int, payload: TaskUpdate):
    if payload.title is None and payload.done is None:
        return JSONResponse(
            status_code=400,
            content={"error": "title or done is required"},
        )
    if payload.title is not None and payload.title == "":
        return JSONResponse(
            status_code=400,
            content={"error": "title cannot be empty"},
        )

    task = storage.update_task(task_id, payload)
    if task is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"},
        )
    return task


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    if not storage.delete_task(task_id):
        return JSONResponse(
            status_code=404,
            content={"error": f"Task {task_id} not found"},
        )
    return Response(status_code=204)
