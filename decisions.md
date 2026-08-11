# Decisions

## BE-04 (A3) — Postgres + Docker + Compose decisions

- **Postgres runs in Docker Compose, not standalone.** `compose.yaml` defines `db` (`postgres:16`) and `api` services. `db` uses a named volume, `taskdata:/var/lib/postgresql/data`, so task data survives `docker compose down` / `docker compose up` cycles, not just app-process restarts. Verified manually: create a row, `down`, `up`, row still present, seed rows not duplicated.
- **`db` is not published to the host.** `compose.yaml` has no `ports:` entry for `db` — Postgres is reachable only from inside the compose network (i.e. by the `api` container, over the hostname `db`), not from `localhost` on the host machine. Inspecting the database is done through `docker compose exec db psql -U postgres -d tasks -c "..."`, not a host-side `psql`/`localhost:5432` connection.
- **`DATABASE_URL` comes from `.env` via `env_file`, not hardcoded in `compose.yaml`.** The `api` service declares `env_file: [.env]`; `.env` (gitignored) is the single source of truth for `DATABASE_URL`, and `.env.example` is the committed template. An earlier draft of `compose.yaml` hardcoded `DATABASE_URL` under `api.environment`, duplicating the same value that also lived in `.env` — `env_file` collapsed that to one source.
- **Storage-layer swap only — routers/schemas untouched.** Only `app/db.py` (connection + schema + seed) and `app/storage.py` (CRUD queries) changed to talk to Postgres. `app/routers/tasks.py`, `app/routers/meta.py`, and `app/schemas.py` are unchanged from the SQLite version — the storage functions' signatures and return types stayed the same, so nothing above the storage layer had to change.
- **`psycopg` (v3) driver, parameterized with `%s`.** SQLite's `?` placeholders became `%s` (the psycopg/Postgres convention). All queries remain parameterized — no string-built SQL — carrying forward the same injection-safety property as the SQLite version. `create_task` uses `INSERT ... RETURNING id, title, done` to get the new row back in one round trip, instead of SQLite's separate `INSERT` + re-`SELECT` by `cursor.lastrowid`.
- **Id behavior changes: `SERIAL` does not reuse ids after delete.** Postgres's `SERIAL PRIMARY KEY` is sequence-backed — once a value is handed out it is never reused, even after the row is deleted. This differs from SQLite's plain `INTEGER PRIMARY KEY` rowid, which reassigned `max(existing id) + 1` and *did* reuse ids (see "Deviations from Week 2 API Behavior" below — that claim of full id-reuse parity held only through the SQLite stage, not past this one). This is a deliberate, accepted tradeoff: no endpoint's status code, response shape, or error body depends on a specific id value, so it doesn't affect the API contract. Seed rows are inserted with explicit ids (1, 2, 3); `init_db()` then calls `setval(pg_get_serial_sequence('tasks','id'), (SELECT MAX(id) FROM tasks))` so the sequence doesn't collide with those explicit ids on the next auto-generated insert.
- **Compose startup ordering: healthcheck + `condition: service_healthy`.** `db` has a `pg_isready`-based healthcheck (2s interval, 10 retries); `api` declares `depends_on: db: condition: service_healthy`. Plain `depends_on` (no condition) only waits for the container to *start*, not for Postgres to actually accept connections — without the healthcheck gate, `api` raced ahead on `docker compose up` and crashed on first boot with a connection/DNS failure before Postgres was ready to accept connections.

## Stage Goals
- Stage 0: Scaffold `decisions.md` and add `tasks.db` / `__pycache__` to `.gitignore` before any DB code lands.
- Stage 1: Add `app/db.py` — schema definition, connection helper, and `init_db()` — without touching the running app yet.
- Stage 2: Wire the app to SQLite — call `db.init_db()` from a FastAPI lifespan handler on startup, and rewrite `app/storage.py` to read/write through `sqlite3` instead of the in-memory list.
- Stage 4: Explore the resulting `tasks.db` directly with DB Browser for SQLite (screenshots in `docs/screenshots/`) as independent evidence the schema and seed data match what `app/db.py` creates, separate from the API's own test coverage.

## Commit-numbering note
This migration's own commits restart the stage count at 0 (`abd0ba9` Stage 0 → `f2f0fa9` Stage 5), separate from Week 2's Stage 0–6 numbering already present earlier in the git log. Two clarifications on stage-to-commit mapping:
- **Stage 3 (update/delete via SQL)** was not split into its own commit — `update_task` and `delete_task` were implemented alongside `list_tasks`/`get_task`/`create_task` in a single pass, all landing in `8382ee3 "Stage 2: wire storage layer to SQLite"`. There was no meaningful way to isolate update/delete from the rest of the storage-layer rewrite without an artificial split, so this note stands in place of a separate commit.
- **Stage 5 (database documentation)** — the bulk of it (README objective/why-SQLite/how-to-run/verify-persistence, and this file) landed in `f2f0fa9`. The DB Browser screenshots and SQL-query evidence added after that are labeled Stage 4 ("explored SQLite") in the git log, since that's what they actually are, rather than opening a second commit also titled "Stage 5".

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

*(This section describes the SQLite stage specifically. The later BE-04/Postgres stage — see the section at the top of this file — intentionally changed id-reuse behavior; that's the one deviation from what's claimed below.)*

- None observed as of the SQLite stage. The HTTP contract (status codes, request/response shapes, 404/400 error bodies, id-reuse semantics) was unchanged from Week 2 — the only difference was that tasks persisted in `tasks.db` across restarts instead of resetting to the 3 seed rows every time the process started. Verified manually: full CRUD cycle, restart-persistence, and post-delete id reuse (`POST` after deleting id 4 reassigns id 4) all behaved identically to Week 2.
- **This id-reuse parity no longer holds as of BE-04.** Postgres's `SERIAL` primary key never reuses a deleted id (unlike SQLite's rowid, used above). Status codes, response shapes, and error bodies are still unchanged — only the specific numeric id values assigned to new rows can now differ from what SQLite would have assigned.
