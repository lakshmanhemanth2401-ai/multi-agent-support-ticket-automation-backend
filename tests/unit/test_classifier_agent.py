from unittest.mock import AsyncMock

import pytest

from app.agents.classifier_agent import ClassifierAgent
from app.llm.ollama_client import OllamaClient, OllamaUnavailableError
from app.llm.structured_output import TicketCategory
from app.schemas.ticket import TicketPriority


@pytest.fixture
def ollama_client() -> AsyncMock:
    return AsyncMock(spec=OllamaClient)


@pytest.mark.asyncio
async def test_classifier_returns_structured_classification(
    ollama_client: AsyncMock,
) -> None:
    ollama_client.chat.return_value = """{
        "category": "security",
        "priority": "urgent",
        "confidence": 0.97,
        "reasoning_summary": "The ticket reports an active account compromise."
    }"""
    agent = ClassifierAgent(client=ollama_client)

    result = await agent.classify(
        title="Account hacked",
        description="An unknown user is changing my account settings.",
    )

    assert result.category is TicketCategory.SECURITY
    assert result.priority is TicketPriority.URGENT
    assert result.confidence == pytest.approx(0.97)
    assert "account compromise" in result.reasoning_summary

    call = ollama_client.chat.await_args.kwargs
    assert call["output_schema"]["title"] == "ClassificationResult"
    assert call["messages"][0]["role"] == "system"
    assert "Account hacked" in call["messages"][1]["content"]


@pytest.mark.asyncio
async def test_classifier_falls_back_when_ollama_is_unavailable(
    ollama_client: AsyncMock,
) -> None:
    ollama_client.chat.side_effect = OllamaUnavailableError("offline")
    agent = ClassifierAgent(client=ollama_client)

    result = await agent.classify(
        title="Cannot log in",
        description="Login fails after submitting credentials.",
    )

    assert result.category is TicketCategory.GENERAL
    assert result.priority is TicketPriority.MEDIUM
    assert result.confidence == 0.0
    assert result.reasoning_summary == (
        "Automated classification unavailable; manual triage required."
    )


@pytest.mark.asyncio
async def test_classifier_falls_back_on_invalid_structured_output(
    ollama_client: AsyncMock,
) -> None:
    ollama_client.chat.return_value = "not-json"
    agent = ClassifierAgent(client=ollama_client)

    result = await agent.classify(
        title="Question",
        description="I need help using a feature.",
    )

    assert result.category is TicketCategory.GENERAL
    assert result.priority is TicketPriority.MEDIUM
    assert result.confidence == 0.0


@pytest.mark.asyncio
async def test_classifier_falls_back_on_out_of_range_confidence(
    ollama_client: AsyncMock,
) -> None:
    ollama_client.chat.return_value = """{
        "category": "technical",
        "priority": "high",
        "confidence": 1.5,
        "reasoning_summary": "A major feature is blocked."
    }"""
    agent = ClassifierAgent(client=ollama_client)

    result = await agent.classify(
        title="Integration stopped",
        description="No events have synced today.",
    )

    assert result.confidence == 0.0
    assert result.category is TicketCategory.GENERAL
