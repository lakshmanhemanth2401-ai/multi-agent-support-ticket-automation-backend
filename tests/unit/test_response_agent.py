from unittest.mock import AsyncMock

import pytest

from app.agents.knowledge_agent import KnowledgeSearchResult
from app.agents.response_agent import ResponseAgent
from app.agents.solution_agent import SolutionResult, SupportingSource
from app.llm.ollama_client import OllamaClient, OllamaUnavailableError
from app.llm.structured_output import ClassificationResult, TicketCategory
from app.rag.vector_store import RetrievalResult
from app.schemas.ticket import TicketPriority


def _context() -> tuple[ClassificationResult, KnowledgeSearchResult, SolutionResult]:
    classification = ClassificationResult(
        category=TicketCategory.ACCOUNT,
        priority=TicketPriority.HIGH,
        confidence=0.91,
        reasoning_summary="The user is blocked by an SSO failure.",
    )
    knowledge = KnowledgeSearchResult(
        results=[
            RetrievalResult(
                content="Confirm application assignment and capture the correlation ID.",
                source="identity/sso_access.md",
                relevance_score=0.89,
                distance=0.11,
                metadata={"title": "SSO Access Runbook"},
            )
        ],
        confidence=0.89,
        sufficient=True,
        query="SSO login failure",
    )
    solution = SolutionResult(
        troubleshooting_steps=[
            "Confirm the user is assigned to the enterprise application.",
            "Capture the failed request correlation ID.",
        ],
        confidence=0.82,
        supporting_sources=[
            SupportingSource(
                source="identity/sso_access.md",
                title="SSO Access Runbook",
                relevance_score=0.89,
            )
        ],
        escalation_required=False,
        summary="Validate assignment and capture trace evidence.",
    )
    return classification, knowledge, solution


@pytest.mark.asyncio
async def test_response_agent_generates_professional_grounded_response() -> None:
    client = AsyncMock(spec=OllamaClient)
    client.chat.return_value = """{
        "subject": "Next steps for your SSO access issue",
        "body": "Thank you for reporting this. Please confirm your application assignment and send the correlation ID shown with the failed request.",
        "confidence": 0.90
    }"""
    classification, knowledge, solution = _context()
    agent = ResponseAgent(client)

    result = await agent.generate(
        title="SSO login fails",
        description="The identity provider returns access denied.",
        classification=classification,
        knowledge=knowledge,
        solution=solution,
    )

    assert result.subject == "Next steps for your SSO access issue"
    assert "Thank you" in result.body
    assert result.confidence == pytest.approx(0.82)
    assert result.escalation_required is False
    assert result.supporting_sources == solution.supporting_sources
    prompt = client.chat.await_args.kwargs["messages"][1]["content"]
    assert "Classification: account" in prompt
    assert "Confirm the user is assigned" in prompt
    assert "identity/sso_access.md" in prompt


@pytest.mark.asyncio
async def test_response_agent_returns_safe_escalation_when_generation_fails() -> None:
    client = AsyncMock(spec=OllamaClient)
    client.chat.side_effect = OllamaUnavailableError("offline")
    classification, knowledge, solution = _context()
    agent = ResponseAgent(client)

    result = await agent.generate(
        title="SSO login fails",
        description="The identity provider returns access denied.",
        classification=classification,
        knowledge=knowledge,
        solution=solution,
    )

    assert result.confidence == 0.0
    assert result.escalation_required is True
    assert "support specialist" in result.body
    assert result.supporting_sources == solution.supporting_sources
