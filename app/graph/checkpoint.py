from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from app.agents.knowledge_agent import KnowledgeSearchResult
from app.agents.response_agent import ResponseResult
from app.agents.solution_agent import SolutionResult, SupportingSource
from app.core.config import settings
from app.llm.structured_output import ClassificationResult, TicketCategory
from app.rag.vector_store import RetrievalResult
from app.schemas.review import ReviewAction, ReviewRead, ReviewStatus
from app.schemas.ticket import TicketPriority


def _postgres_connection_string(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def checkpoint_serializer() -> JsonPlusSerializer:
    return JsonPlusSerializer(
        allowed_msgpack_modules=[
            ClassificationResult,
            TicketCategory,
            TicketPriority,
            KnowledgeSearchResult,
            RetrievalResult,
            SolutionResult,
            SupportingSource,
            ResponseResult,
            ReviewRead,
            ReviewStatus,
            ReviewAction,
        ]
    )


@asynccontextmanager
async def workflow_checkpointer() -> AsyncIterator[Any]:
    """Provide durable PostgreSQL checkpoints, with memory only for SQLite tests/dev."""
    if not settings.database_url.startswith("postgresql"):
        yield InMemorySaver()
        return

    async with AsyncPostgresSaver.from_conn_string(
        _postgres_connection_string(settings.database_url), serde=checkpoint_serializer()
    ) as saver:
        await saver.setup()
        yield saver
