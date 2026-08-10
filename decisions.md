# Decisions

## Stage Goals
- Stage 0: Scaffold `decisions.md` and add `tasks.db` / `__pycache__` to `.gitignore` before any DB code lands.
- Stage 1: Add `app/db.py` — schema definition, connection helper, and `init_db()` — without touching the running app yet.
- Stage 2: Wire the app to SQLite — call `db.init_db()` from a FastAPI lifespan handler on startup, and rewrite `app/storage.py` to read/write through `sqlite3` instead of the in-memory list.

## Key Decisions & Tradeoffs
- **Per-call connections, not a shared global one.** `db.get_connection()` opens a fresh `sqlite3.Connection` per call rather than reusing one at module scope. FastAPI runs sync endpoints in a threadpool, and `sqlite3` connections are not safe to share across threads, so a shared connection would risk cross-request corruption under concurrent requests.
- **Plain `INTEGER PRIMARY KEY`, no `AUTOINCREMENT`.** SQLite's rowid-alias primary key reassigns new rows `max(existing id) + 1` and reuses ids after the highest-id row is deleted. This exactly reproduces the Week 2 in-memory `max(id) + 1` logic (including id reuse), whereas `AUTOINCREMENT` would permanently retire deleted ids and silently change API behavior between weeks.
- **Startup wiring via FastAPI `lifespan`, not module-level code.** `db.init_db()` runs inside an `asynccontextmanager` passed to `FastAPI(lifespan=...)` so the schema/seed step happens once, deterministically, before the app accepts requests — instead of as a side effect of importing `app.main` (which would fire on `pytest` collection, docs generation, etc.).
- **Seed only when the table is empty.** `init_db()` is safe to call on every process start (`CREATE TABLE IF NOT EXISTS` is a no-op after the first run) and only inserts the 3 seed rows when `COUNT(*) = 0`, so restarting the server never duplicates seed data or clobbers real writes.
- **`done` stored as `BOOLEAN` (0/1), cast at the boundary.** SQLite has no native boolean type. `storage._row_to_task()` is the single place that casts `row["done"]` back to Python `bool`, keeping that detail invisible to the router and schema layers.

## SQL Choices (schema + parameterization)
```sql
CREATE TABLE IF NOT EXISTS tasks (
    id    INTEGER PRIMARY KEY,
    title TEXT    NOT NULL,
    done  BOOLEAN NOT NULL DEFAULT 0
);
```
- All queries use `?` placeholders with parameters passed as a tuple (e.g. `"SELECT ... WHERE id = ?;", (task_id,)`) — no string formatting or f-strings ever build SQL, which rules out SQL injection from user-supplied `title`/`id` values.
- `create_task` inserts without an explicit `id` (relies on rowid assignment) then re-selects the row by `cursor.lastrowid` to build the response, rather than trusting in-memory state.
- `update_task` reads the existing row first, merges only the fields the caller supplied (mirroring the old in-memory partial-update behavior), then writes both columns back in one `UPDATE`.
- `delete_task` uses `cursor.rowcount > 0` to report whether a row was actually deleted, so the router can still return its existing 404 for unknown ids.

## Deviations from Week 2 API Behavior
- None observed. The HTTP contract (status codes, request/response shapes, 404/400 error bodies, id-reuse semantics) is unchanged — the only difference is that tasks now persist in `tasks.db` across restarts instead of resetting to the 3 seed rows every time the process starts. Verified manually: full CRUD cycle, restart-persistence, and post-delete id reuse (`POST` after deleting id 4 reassigns id 4) all behave identically to Week 2.
