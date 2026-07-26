# Task API

A small FastAPI CRUD API for managing an in-memory to-do list. No database or files — tasks live in memory for the lifetime of the server process. Built for FlyRank Week 2 BE-01.

## Install & run

Requires Python 3.12.3 (Ubuntu).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The server starts at [http://localhost:8000](http://localhost:8000).  
Interactive docs (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)

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
curl -i -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title":"Buy milk"}'
```

```
HTTP/1.1 201 Created
date: Sun, 26 Jul 2026 18:49:52 GMT
server: uvicorn
content-length: 40
content-type: application/json

{"id":4,"title":"Buy milk","done":false}
```

## Swagger UI

![Swagger UI for Task API](docs/docs-swagger.png)
