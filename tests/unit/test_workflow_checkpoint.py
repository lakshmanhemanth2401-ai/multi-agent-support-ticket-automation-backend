import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.core.config import settings
from app.graph.checkpoint import (
    _postgres_connection_string,
    checkpoint_serializer,
    workflow_checkpointer,
)
from app.llm.structured_output import ClassificationResult, TicketCategory
from app.schemas.ticket import TicketPriority


def test_postgres_connection_string_removes_sqlalchemy_driver() -> None:
    assert _postgres_connection_string(
        "postgresql+psycopg://user:password@postgres/support"
    ) == "postgresql://user:password@postgres/support"


def test_strict_checkpoint_serializer_preserves_domain_types() -> None:
    serializer = checkpoint_serializer()
    value = ClassificationResult(
        category=TicketCategory.TECHNICAL,
        priority=TicketPriority.HIGH,
        confidence=0.9,
        reasoning_summary="Technical failure",
    )

    restored = serializer.loads_typed(serializer.dumps_typed(value))

    assert isinstance(restored, ClassificationResult)
    assert restored.category is TicketCategory.TECHNICAL
    assert restored.priority is TicketPriority.HIGH


@pytest.mark.asyncio
async def test_sqlite_uses_in_memory_checkpoint(monkeypatch) -> None:
    monkeypatch.setattr(settings, "database_url", "sqlite+pysqlite:///:memory:")

    async with workflow_checkpointer() as checkpointer:
        assert isinstance(checkpointer, InMemorySaver)
