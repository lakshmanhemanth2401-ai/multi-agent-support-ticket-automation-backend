import pytest
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from typing import TypedDict

from app.core.config import settings
from app.graph.checkpoint import (
    _postgres_connection_string,
    checkpoint_serializer,
    workflow_checkpointer,
)
from app.llm.structured_output import ClassificationResult, TicketCategory
from app.schemas.ticket import TicketPriority


def test_postgres_connection_string_removes_sqlalchemy_driver() -> None:
    assert (
        _postgres_connection_string("postgresql+psycopg://user:password@postgres/support")
        == "postgresql://user:password@postgres/support"
    )


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
async def test_sqlite_checkpoint_survives_reopen(monkeypatch, tmp_path) -> None:
    class State(TypedDict):
        value: int

    checkpoint_path = tmp_path / "workflow-checkpoints.db"
    monkeypatch.setattr(settings, "database_url", "sqlite+pysqlite:///:memory:")
    monkeypatch.setattr(settings, "workflow_checkpoint_path", str(checkpoint_path))
    config = {"configurable": {"thread_id": "persistent-thread"}}

    builder = StateGraph(State)
    builder.add_node("increment", lambda state: {"value": state["value"] + 1})
    builder.add_edge(START, "increment")
    builder.add_edge("increment", END)

    async with workflow_checkpointer() as checkpointer:
        assert isinstance(checkpointer, AsyncSqliteSaver)
        graph = builder.compile(checkpointer=checkpointer)
        await graph.ainvoke({"value": 1}, config)

    async with workflow_checkpointer() as reopened:
        graph = builder.compile(checkpointer=reopened)
        snapshot = await graph.aget_state(config)

    assert snapshot.values["value"] == 2
