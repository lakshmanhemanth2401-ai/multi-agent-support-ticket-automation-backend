from unittest.mock import AsyncMock

import pytest

from app.agents.knowledge_agent import KnowledgeSearchResult
from app.agents.solution_agent import SolutionAgent
from app.llm.ollama_client import OllamaClient, OllamaUnavailableError
from app.llm.structured_output import ClassificationResult, TicketCategory
from app.rag.vector_store import RetrievalResult
from app.schemas.ticket import TicketPriority


def _classification() -> ClassificationResult:
    return ClassificationResult(
        category=TicketCategory.ACCOUNT,
        priority=TicketPriority.HIGH,
        confidence=0.90,
        reasoning_summary="The user cannot authenticate through SSO.",
    )


def _knowledge(*, sufficient: bool = True, confidence: float = 0.86) -> KnowledgeSearchResult:
    return KnowledgeSearchResult(
        results=[
            RetrievalResult(
                content="Check tenant assignment and capture the correlation ID.",
                source="identity/sso_access.md",
                relevance_score=confidence,
                distance=1.0 - confidence,
                metadata={"title": "SSO Access Runbook", "document_id": "IAM-104"},
            )
        ],
        confidence=confidence,
        sufficient=sufficient,
        reason=None if sufficient else "Retrieved knowledge is insufficient.",
        query="SSO login failure",
    )


@pytest.mark.asyncio
async def test_solution_agent_generates_steps_and_uses_retrieved_sources() -> None:
    client = AsyncMock(spec=OllamaClient)
    client.chat.return_value = """{
        "troubleshooting_steps": [
            "Confirm the user is assigned to the enterprise application.",
            "Capture the failed request correlation ID.",
            "Retry in a private browser window."
        ],
        "confidence": 0.82,
        "summary": "Validate assignment and isolate stale browser state."
    }"""
    agent = SolutionAgent(client=client, minimum_confidence=0.55)

    result = await agent.generate(
        title="SSO login fails",
        description="The identity provider returns an access error.",
        classification=_classification(),
        knowledge=_knowledge(),
    )

    assert len(result.troubleshooting_steps) == 3
    assert result.confidence == pytest.approx(0.82)
    assert result.escalation_required is False
    assert result.supporting_sources[0].source == "identity/sso_access.md"
    assert result.supporting_sources[0].title == "SSO Access Runbook"
    prompt = client.chat.await_args.kwargs["messages"][1]["content"]
    assert "Classification category: account" in prompt
    assert "identity/sso_access.md" in prompt
    assert "Check tenant assignment" in prompt


@pytest.mark.asyncio
async def test_solution_agent_escalates_without_calling_llm_when_knowledge_is_weak() -> None:
    client = AsyncMock(spec=OllamaClient)
    agent = SolutionAgent(client=client)

    result = await agent.generate(
        title="SSO login fails",
        description="No matching runbook was found.",
        classification=_classification(),
        knowledge=_knowledge(sufficient=False, confidence=0.20),
    )

    assert result.escalation_required is True
    assert result.troubleshooting_steps == []
    assert "insufficient" in (result.escalation_reason or "")
    client.chat.assert_not_awaited()


@pytest.mark.asyncio
async def test_solution_agent_escalates_when_ollama_fails() -> None:
    client = AsyncMock(spec=OllamaClient)
    client.chat.side_effect = OllamaUnavailableError("offline")
    agent = SolutionAgent(client=client)

    result = await agent.generate(
        title="SSO login fails",
        description="The identity provider returns an access error.",
        classification=_classification(),
        knowledge=_knowledge(),
    )

    assert result.escalation_required is True
    assert result.confidence == 0.0
    assert "generation failed" in (result.escalation_reason or "")
    assert result.supporting_sources[0].source == "identity/sso_access.md"


@pytest.mark.asyncio
async def test_solution_agent_escalates_low_confidence_plan() -> None:
    client = AsyncMock(spec=OllamaClient)
    client.chat.return_value = """{
        "troubleshooting_steps": ["Collect the correlation ID."],
        "confidence": 0.30,
        "summary": "Evidence is limited."
    }"""
    agent = SolutionAgent(client=client, minimum_confidence=0.55)

    result = await agent.generate(
        title="SSO login fails",
        description="The error is intermittent.",
        classification=_classification(),
        knowledge=_knowledge(),
    )

    assert result.confidence == pytest.approx(0.30)
    assert result.escalation_required is True
    assert "below" in (result.escalation_reason or "")
