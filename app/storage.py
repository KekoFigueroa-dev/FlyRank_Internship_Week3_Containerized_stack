from app import db
from app.schemas import Task, TaskUpdate


def _row_to_task(row) -> Task:
    # SQLite has no native boolean type; `done` is stored as 0/1, so cast
    # explicitly back to bool here. Keeps that detail invisible to callers.
    return Task(id=row["id"], title=row["title"], done=bool(row["done"]))


def list_tasks() -> list[Task]:
    with db.get_connection() as connection:
        rows = connection.execute(
            "SELECT id, title, done FROM tasks ORDER BY id;"
        ).fetchall()
    return [_row_to_task(row) for row in rows]


def get_task(task_id: int) -> Task | None:
    with db.get_connection() as connection:
        row = connection.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?;",
            (task_id,),
        ).fetchone()
    return _row_to_task(row) if row is not None else None


def create_task(title: str) -> Task:
    with db.get_connection() as connection:
        # No explicit id: plain INTEGER PRIMARY KEY (no AUTOINCREMENT)
        # assigns max(existing id) + 1, reproducing the Week 2 in-memory
        # id logic including reuse after the highest id is deleted.
        cursor = connection.execute(
            "INSERT INTO tasks (title, done) VALUES (?, 0);",
            (title,),
        )
        new_id = cursor.lastrowid
        row = connection.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?;",
            (new_id,),
        ).fetchone()
    return _row_to_task(row)


def update_task(task_id: int, update: TaskUpdate) -> Task | None:
    with db.get_connection() as connection:
        row = connection.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?;",
            (task_id,),
        ).fetchone()
        if row is None:
            return None

        # Merge only the provided fields in Python (mirrors the old
        # in-memory update_task), then write both columns back.
        new_title = update.title if update.title is not None else row["title"]
        new_done = update.done if update.done is not None else bool(row["done"])

        connection.execute(
            "UPDATE tasks SET title = ?, done = ? WHERE id = ?;",
            (new_title, new_done, task_id),
        )
    return Task(id=task_id, title=new_title, done=new_done)


def delete_task(task_id: int) -> bool:
    with db.get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM tasks WHERE id = ?;",
            (task_id,),
        )
    return cursor.rowcount > 0
