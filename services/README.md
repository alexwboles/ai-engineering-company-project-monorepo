# services

All API and service endpoints for this monorepo must be implemented under this directory.

## Convention

- Keep service code separate from UI apps under uis/.
- Reuse shared types from packages/shared.
- Reuse existing business logic modules instead of duplicating domain logic.

## Async task worker

Redis is the Celery broker and result backend. Set `REDIS_URL` to the shared
broker, for example `redis://localhost:6379/0` for a local worker or
`redis://redis:6379/0` inside Docker Compose.

Start the API and the worker as separate processes:

```powershell
uv run --project services/api uvicorn services.api.main:app --reload
uv run --project services/api celery -A services.celery_app worker --loglevel=info
```

For the development stack, `docker compose up api worker redis flower` starts
the worker independently of FastAPI. Flower is available at
`http://localhost:5555`; stop it with `docker compose stop worker flower` or
stop the full stack with `docker compose down`.

The worker handles `POST /api/incidents/analyze` in the background. The API
stages the upload to a file and sends only that file path in the Celery
message, returning `202` with a `task_id`. Poll `GET /tasks/{task_id}` for
`pending`, `started`, `success`, or `failure`.
