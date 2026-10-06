# Multi-Agent Support Ticket Automation Backend

FastAPI backend that classifies enterprise support tickets, retrieves indexed knowledge,
generates troubleshooting guidance and customer responses, and pauses for human approval.

## Architecture

- FastAPI with OpenAPI contracts
- SQLAlchemy and Alembic with PostgreSQL
- Ollama agents and embeddings
- ChromaDB semantic retrieval
- LangGraph with PostgreSQL checkpoints
- Argon2 password hashes and rotating JWT refresh sessions
- Prometheus, structured logs, request IDs, and Grafana

No default users or credentials are created.

## Environment variables

Copy `.env.example` to `.env`, replace every `CHANGE_ME`, and never commit `.env`.

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL URL; SQLite is supported for development/tests |
| `JWT_SECRET` | Random token-signing secret of at least 32 characters |
| `JWT_ISSUER`, `JWT_AUDIENCE` | JWT validation boundaries |
| `ACCESS_TOKEN_MINUTES`, `REFRESH_TOKEN_DAYS` | Token lifetimes |
| `CORS_ALLOWED_ORIGINS` | JSON list of explicit frontend origins |
| `OLLAMA_BASE_URL`, `OLLAMA_MODEL` | Ollama chat configuration |
| `OLLAMA_EMBEDDING_MODEL` | Knowledge embedding model |
| `CHROMA_PERSIST_DIRECTORY` | ChromaDB persistence directory |
| `POSTGRES_*`, `GRAFANA_ADMIN_*` | Compose service configuration |

Inject production secrets through a platform secret manager.

## Local setup

```bash
python -m pip install -e ".[dev]"
python -m alembic upgrade head
ollama pull llama3.2:3b
ollama pull embeddinggemma
python -m scripts.create_user --email admin@example.com --role administrator
python -m uvicorn app.main:app --reload
```

The user command securely prompts for a password. Passwords require at least 12 characters
and are stored as Argon2 hashes. OpenAPI is at `http://localhost:8000/docs`.

## Authentication and roles

Send `Authorization: Bearer <access_token>`.

| Role | Permissions |
| --- | --- |
| `support_agent` | Tickets, workflows, and knowledge |
| `reviewer` | Support permissions plus reviews and audit history |
| `administrator` | All permissions, including `/metrics` |

Routes:

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

Refresh tokens rotate and are revoked on use or logout. Their identifiers are persisted so
replay attempts can be rejected.

## API routes

- `POST /api/v1/tickets`
- `GET /api/v1/tickets?offset=0&limit=100`
- `GET /api/v1/tickets/{ticket_id}`
- `POST /api/v1/workflows/tickets/{ticket_id}`
- `GET /api/v1/workflows/tickets/{ticket_id}`
- `GET /api/v1/workflows/{thread_id}`
- `POST /api/v1/workflows/{thread_id}/review`
- `GET /api/v1/reviews?status=pending&offset=0&limit=100`
- `GET /api/v1/reviews/{review_id}`
- `GET /api/v1/tickets/{ticket_id}/audit?offset=0&limit=100`
- `GET /api/v1/knowledge/documents?offset=0&limit=100`
- `POST /api/v1/knowledge/search`
- `GET /health` and `GET /api/v1/health` (public)
- `GET /metrics` (administrator only)

List endpoints return `items` plus `pagination` containing `offset`, `limit`, and `total`.
Knowledge search accepts `query` and `top_k`, returns relevance scores from 0–1, and returns
`{"items": [], "count": 0}` when nothing is found.

## Workflow

Classifier → Knowledge → Solution → Response pauses for human review. Both paused and completed
responses expose category, priority, safe classification confidence, retrieved chunks and
sources, solution steps, supporting sources, generated response, confidence, escalation state,
and review status. Internal reasoning, retrieval queries, prompts, credentials, and customer
secrets are not returned.

Actions are `approve`, `reject`, `edit`, and `regenerate`. Reject and regenerate return through
solution/response generation; approve and edit finish the workflow. Transitions and review
actions are recorded in the ticket audit trail.

Creating a ticket automatically queues this workflow. The ticket response exposes
`workflow_thread_id` and `analysis_status` (`queued`, `running`, `awaiting_review`, `completed`,
or `failed`). The ticket workflow GET endpoint retrieves the automatic result. The POST endpoint
is idempotent and returns the existing result instead of starting duplicate agent runs.

For the Vite frontend, set `VITE_API_BASE_URL=http://localhost:8000/api/v1`. The backend
`CORS_ALLOWED_ORIGINS` must contain the exact browser origin (normally
`http://localhost:5173`). Do not include `/api/v1` in the CORS origin.

## Knowledge ingestion

```bash
python -m scripts.ingest_knowledge --directory data/knowledge_base
```

This cleans and chunks documents, updates SQL records, refreshes matching ChromaDB sources,
preserves metadata, and verifies SQL/vector chunk counts.

## Docker

```bash
docker compose up --build -d
```

The API applies Alembic migrations before startup. Compose includes PostgreSQL, Ollama,
Prometheus, and Grafana and requires PostgreSQL, Grafana, and JWT secrets from the environment.
The one-shot `ollama-init` service downloads both configured Ollama models before the API starts.

## Verification

```bash
python -m pytest -q
python -m ruff check app tests migrations scripts
python -m ruff format --check app tests migrations scripts
python -m mypy app
```

CI runs tests, linting, formatting, type checking, migrations, and a production image build.
