import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

# Loads .env for local (non-Docker) runs. In Docker Compose, DATABASE_URL is
# injected directly as a container environment variable, so this is a no-op
# there (load_dotenv doesn't override already-set env vars, and silently
# does nothing if .env doesn't exist).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DATABASE_URL = os.environ["DATABASE_URL"]

# Schema: SERIAL PRIMARY KEY (sequence-backed autoincrement). Unlike SQLite's
# plain rowid, a Postgres sequence never reassigns or reuses ids after a
# delete — that's a Postgres-idiomatic tradeoff we accept; the API contract
# (status codes, error bodies, response shapes) doesn't depend on exact ids.
_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id    SERIAL PRIMARY KEY,
    title TEXT    NOT NULL,
    done  BOOLEAN NOT NULL DEFAULT FALSE
);
"""

# Seed rows, inserted only when the table is empty (see init_db). Mirrors
# the 3 hardcoded seed tasks from the SQLite version so first-run behavior
# is identical.
_SEED_ROWS = [
    (1, "Learn FastAPI", False),
    (2, "Build CRUD API", False),
    (3, "Commit Stage 2", True),
]


def get_connection() -> psycopg.Connection:
    # Opens a short-lived connection per call rather than sharing one
    # global connection/pool, mirroring the SQLite version's connection
    # lifecycle for a minimal-diff swap.
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db() -> None:
    # Called on app startup. Safe to call repeatedly: CREATE TABLE IF NOT
    # EXISTS is a no-op after the first run, and the seed insert only fires
    # when the table is empty.
    with get_connection() as connection:
        connection.execute(_CREATE_TABLE_SQL)

        row_count = connection.execute(
            "SELECT COUNT(*) AS count FROM tasks;"
        ).fetchone()["count"]
        if row_count == 0:
            with connection.cursor() as cursor:
                cursor.executemany(
                    "INSERT INTO tasks (id, title, done) VALUES (%s, %s, %s);",
                    _SEED_ROWS,
                )
            # Explicit ids were inserted above, so advance the SERIAL
            # sequence past them; otherwise the next INSERT without an
            # explicit id would collide with seed id 3.
            connection.execute(
                "SELECT setval(pg_get_serial_sequence('tasks', 'id'), "
                "(SELECT MAX(id) FROM tasks));"
            )
