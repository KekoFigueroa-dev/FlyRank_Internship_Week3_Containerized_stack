import sqlite3
from pathlib import Path

# Anchor the DB file to the project root (parent of app/), not the process's
# current working directory, so it lands in the same place no matter where
# `uvicorn` is launched from.
DB_PATH = Path(__file__).resolve().parent.parent / "tasks.db"

# Schema: plain `INTEGER PRIMARY KEY` (rowid alias), deliberately WITHOUT
# AUTOINCREMENT. Plain rowids get reassigned as max(existing id) + 1 and can
# be reused after the highest-id row is deleted — this matches Week 2's
# in-memory `max(id) + 1` logic exactly, including id reuse. AUTOINCREMENT
# would block reuse and silently change behavior.
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id    INTEGER PRIMARY KEY,
    title TEXT    NOT NULL,
    done  BOOLEAN NOT NULL DEFAULT 0
);
"""

# Seed rows, inserted only when the table is empty (see init_db). Mirrors
# the 3 hardcoded Week 2 in-memory tasks so first-run behavior is identical.
_SEED_ROWS = [
    (1, "Learn FastAPI", 0),
    (2, "Build CRUD API", 0),
    (3, "Commit Stage 2", 1),
]


def get_connection() -> sqlite3.Connection:
    # Opens a short-lived connection per call rather than sharing one
    # global connection: FastAPI runs sync endpoints in a threadpool, and
    # sqlite3 connections aren't safe to share across threads.
    connection = sqlite3.connect(DB_PATH)
    # Row factory lets callers access columns by name (row["title"]) instead
    # of positional index, so storage.py stays readable.
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    # Called on app startup (Stage 2) and directly in tests here in Stage 1.
    # Safe to call repeatedly: CREATE TABLE IF NOT EXISTS is a no-op after
    # the first run, and the seed insert only fires when the table is empty.
    with get_connection() as connection:
        connection.execute(_CREATE_TABLE_SQL)

        # Only seed on a truly empty table, so re-running init_db() (e.g. on
        # every app restart) never re-inserts or duplicates the seed rows.
        row_count = connection.execute("SELECT COUNT(*) FROM tasks;").fetchone()[0]
        if row_count == 0:
            connection.executemany(
                "INSERT INTO tasks (id, title, done) VALUES (?, ?, ?);",
                _SEED_ROWS,
            )
