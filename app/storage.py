from app.schemas import Task

tasks: list[Task] = [
    Task(id=1, title="Learn FastAPI", done=False),
    Task(id=2, title="Build CRUD API", done=False),
    Task(id=3, title="Commit Stage 2", done=True),
]


def list_tasks() -> list[Task]:
    return tasks


def get_task(task_id: int) -> Task | None:
    for task in tasks:
        if task.id == task_id:
            return task
    return None
