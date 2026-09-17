from unittest.mock import Mock

import pytest

from app.agents.knowledge_agent import KnowledgeSearchAgent
from app.llm.structured_output import ClassificationResult, TicketCategory
from app.rag.vector_store import RetrievalResult
from app.schemas.ticket import TicketPriority


def _classification() -> ClassificationResult:
    return ClassificationResult(
        category=TicketCategory.BILLING,
        priority=TicketPriority.HIGH,
        confidence=0.92,
        reasoning_summary="A duplicate settled charge blocks billing reconciliation.",
    )


@pytest.mark.asyncio
async def test_knowledge_agent_passes_classification_into_search() -> None:
    retriever = Mock()
    retriever.retrieve.return_value = [
        RetrievalResult(
            content="Verify whether both charges are settled.",
            source="billing/duplicate_charge.md",
            relevance_score=0.88,
            distance=0.12,
            metadata={"title": "Duplicate Charge Policy"},
        )
    ]
    agent = KnowledgeSearchAgent(retriever, minimum_relevance=0.40)

    result = await agent.search(
        title="Charged twice",
        description="Two card charges settled for the same invoice.",
        classification=_classification(),
        top_k=3,
    )

    assert result.sufficient is True
    assert result.confidence == pytest.approx(0.88)
    query = retriever.retrieve.call_args.args[0]
    assert "Support category: billing" in query
    assert "Priority: high" in query
    assert "Charged twice" in query
    assert retriever.retrieve.call_args.kwargs == {"top_k": 3}


@pytest.mark.asyncio
async def test_knowledge_agent_marks_low_relevance_as_insufficient() -> None:
    retriever = Mock()
    retriever.retrieve.return_value = [
        RetrievalResult(
            content="General account guidance.",
            source="general/account.md",
            relevance_score=0.21,
            distance=0.79,
        )
    ]
    agent = KnowledgeSearchAgent(retriever, minimum_relevance=0.40)

    result = await agent.search(
        title="Charged twice",
        description="Two charges settled.",
        classification=_classification(),
    )

    assert result.sufficient is False
    assert "below" in (result.reason or "")


@pytest.mark.asyncio
async def test_knowledge_agent_handles_retrieval_failure() -> None:
    retriever = Mock()
    retriever.retrieve.side_effect = RuntimeError("vector store unavailable")
    agent = KnowledgeSearchAgent(retriever)

    result = await agent.search(
        title="Charged twice",
        description="Two charges settled.",
        classification=_classification(),
    )

    assert result.sufficient is False
    assert result.confidence == 0.0
    assert result.results == []
    assert "failed" in (result.reason or "").lower()
