from app.schemas import Task, TaskUpdate

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


def create_task(title: str) -> Task:
    next_id = max((task.id for task in tasks), default=0) + 1
    task = Task(id=next_id, title=title, done=False)
    tasks.append(task)
    return task


def update_task(task_id: int, update: TaskUpdate) -> Task | None:
    task = get_task(task_id)
    if task is None:
        return None
    if update.title is not None:
        task.title = update.title
    if update.done is not None:
        task.done = update.done
    return task


def delete_task(task_id: int) -> bool:
    for index, task in enumerate(tasks):
        if task.id == task_id:
            tasks.pop(index)
            return True
    return False
