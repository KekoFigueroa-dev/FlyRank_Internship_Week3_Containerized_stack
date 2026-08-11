# Task API

A small FastAPI CRUD API for managing a to-do list, backed by Postgres running in Docker. The whole stack (API + database) runs with a single command: `docker compose up`. Built for FlyRank Week 3 BE-04, migrated from the SQLite version (Week 3 BE-01/02).

## Objective

Week 3's earlier stage swapped an in-memory list for SQLite. This stage (BE-04) swaps SQLite for Postgres and containerizes the whole stack, **without changing any observable API behavior**: the same 5 endpoints, the same status codes (200/201/204/400/404), and the same error JSON shape/wording as before. The architecture proof is that only the storage layer (`app/db.py` + `app/storage.py`) changed — routes and request/response schemas were untouched.

Data now lives in a named Docker volume (`taskdata`), so it survives `docker compose down` / `docker compose up` cycles, not just app restarts.

## Run it

Requires Docker and Docker Compose (`docker compose version`).

```bash
cp .env.example .env   # not strictly required for compose (it injects DATABASE_URL
                        # directly), but this is how a non-containerized run would get it
docker compose up
```

That builds the API image, starts Postgres with a named volume, waits for Postgres to report healthy (`pg_isready`), then starts the API. On first boot the app creates the `tasks` table and seeds 3 tasks — seeding is skipped on every later boot once the table has rows.

The server is at [http://localhost:8000](http://localhost:8000).
Interactive docs (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)

## Environment

| Variable | Where it's set | Example |
|---|---|---|
| `DATABASE_URL` | `.env` (local/non-compose runs) or `compose.yaml` `environment:` (compose runs) | `postgres://postgres:dev@localhost:5432/tasks` (local) / `postgres://postgres:dev@db:5432/tasks` (compose — host is the service name `db`, not `localhost`) |

`.env` is gitignored; `.env.example` is the committed template. Never commit real secrets.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | API name, version, and endpoint list |
| GET | `/health` | Health check (`{"status":"ok"}`) |
| GET | `/tasks` | List all tasks |
| GET | `/tasks/{id}` | Get a task by id |
| POST | `/tasks` | Create a task (`{"title":"..."}`) |
| PUT | `/tasks/{id}` | Partial update (`title` and/or `done`) |
| DELETE | `/tasks/{id}` | Delete a task (204 empty body) |

## Example `curl` output

```bash
curl -i http://localhost:8000/tasks
```

```
HTTP/1.1 200 OK
date: Tue, 11 Aug 2026 04:28:42 GMT
server: uvicorn
content-length: 197
content-type: application/json

[{"id":1,"title":"Learn FastAPI","done":false},{"id":2,"title":"Build CRUD API","done":false},{"id":3,"title":"Commit Stage 2","done":true},{"id":4,"title":"Persisted across restart","done":false}]
```

(That 4th row is the one created in the persistence proof below — a fresh `docker compose up` shows only the 3 seed rows.)

## Database proof

Connecting into the running `db` service and inspecting the schema/data directly:

```bash
docker compose exec db psql -U postgres -d tasks -c "\dt"
```

```
         List of relations
 Schema | Name  | Type  |  Owner
--------+-------+-------+----------
 public | tasks | table | postgres
(1 row)
```

```bash
docker compose exec db psql -U postgres -d tasks -c "SELECT * FROM tasks;"
```

```
 id |          title           | done
----+--------------------------+------
  1 | Learn FastAPI            | f
  2 | Build CRUD API           | f
  3 | Commit Stage 2           | t
  4 | Persisted across restart | f
(4 rows)
```

## Verify persistence

This is the core proof for this stage — data now survives `docker compose down`, not just a container restart, because it lives in the named `taskdata` volume rather than inside the container filesystem.

```bash
# 1. Bring the stack up
docker compose up -d

# 2. Create a task
curl -s -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Persisted across restart"}'
# -> {"id":4,"title":"Persisted across restart","done":false}

# 3. Tear the stack down (containers + network removed; volume is NOT removed)
docker compose down

# 4. Bring it back up
docker compose up -d

# 5. Confirm the task from step 2 is still there
curl -s http://localhost:8000/tasks
# -> still includes id 4, and the seed rows were NOT duplicated
```

To reset to a clean slate (fresh seed, no prior data), remove the volume explicitly: `docker compose down -v`.

## API parity with the SQLite version

Every status code (`200`/`201`/`204`/`400`/`404`) and every error body (e.g. `{"error":"Task 999 not found"}`) behave identically to the SQLite version — verified with the full CRUD `curl` sequence (create/read/update/delete, including every validation error case) against the containerized stack. The one intentional behavior difference: Postgres's `SERIAL` id column never reuses an id after a row is deleted (SQLite's plain rowid did); the API contract doesn't depend on specific id values, so this doesn't affect any endpoint's status code or response shape.

## Decisions

Design decisions and tradeoffs for the original SQLite migration (schema choices, parameterized query patterns) are documented in [`decisions.md`](decisions.md). The Postgres/Docker migration reused that same storage-layer swap pattern: only `app/db.py` and `app/storage.py` changed, `app/routers/tasks.py` and `app/schemas.py` were untouched.
