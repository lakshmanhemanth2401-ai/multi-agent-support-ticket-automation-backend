# Multi-Agent Support Ticket Automation Backend

FastAPI service that classifies enterprise support tickets, retrieves relevant knowledge,
generates troubleshooting guidance and customer responses, and pauses for human approval.

## Features

- PostgreSQL persistence through SQLAlchemy and Alembic
- Ollama classification, solution, and response agents
- ChromaDB semantic knowledge retrieval
- LangGraph workflow with approve, reject, edit, and regenerate review actions
- Durable PostgreSQL workflow checkpoints in deployed environments
- Audit history, structured errors/logging, request IDs, Prometheus metrics, and Grafana

## Local setup

1. Copy `.env.example` to `.env` and replace every `CHANGE_ME` value.
2. Install Python 3.11 dependencies:

   ```bash
   python -m pip install -e ".[dev]"
   ```

3. Apply migrations and start the API:

   ```bash
   python -m alembic upgrade head
   python -m uvicorn app.main:app --reload
   ```

The API documentation is available at `http://localhost:8000/docs` and metrics at
`http://localhost:8000/metrics`.

## Docker

After configuring `.env`:

```bash
docker compose up --build -d
```

The API container applies Alembic migrations before starting. PostgreSQL, Ollama,
Prometheus, and Grafana are included in the Compose stack.

## Main endpoints

- `POST /api/v1/tickets` — create a ticket
- `GET /api/v1/tickets` — list tickets
- `POST /api/v1/workflows/tickets/{ticket_id}` — process a ticket and pause for review
- `GET /api/v1/workflows/{thread_id}` — inspect durable workflow state
- `POST /api/v1/workflows/{thread_id}/review` — approve, reject, edit, or regenerate
- `GET /api/v1/reviews` — list review records
- `GET /api/v1/tickets/{ticket_id}/audit` — view sanitized audit history
- `GET /health` and `GET /metrics` — operational endpoints

## Quality checks

```bash
python -m ruff check app tests
python -m pytest -q
```

CI runs linting, the complete test suite, migrations, and a production container build.
