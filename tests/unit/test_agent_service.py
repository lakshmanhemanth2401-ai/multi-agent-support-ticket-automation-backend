from unittest.mock import AsyncMock

import pytest

from app.agents.knowledge_agent import KnowledgeSearchResult
from app.agents.solution_agent import SolutionResult
from app.llm.structured_output import ClassificationResult, TicketCategory
from app.schemas.ticket import TicketPriority
from app.services.agent_service import AgentService


@pytest.mark.asyncio
async def test_agent_service_passes_outputs_through_resolution_pipeline() -> None:
    classification = ClassificationResult(
        category=TicketCategory.TECHNICAL,
        priority=TicketPriority.HIGH,
        confidence=0.91,
        reasoning_summary="The API is unavailable.",
    )
    knowledge = KnowledgeSearchResult(confidence=0.85, sufficient=True)
    solution = SolutionResult(
        troubleshooting_steps=["Check the public status page."],
        confidence=0.80,
        escalation_required=False,
        summary="Check platform health first.",
    )
    classifier = AsyncMock()
    classifier.classify.return_value = classification
    knowledge_service = AsyncMock()
    knowledge_service.search_for_ticket.return_value = knowledge
    solution_agent = AsyncMock()
    solution_agent.generate.return_value = solution
    service = AgentService(
        classifier=classifier,
        knowledge_service=knowledge_service,
        solution_agent=solution_agent,
    )

    resolution = await service.resolve_ticket(
        title="API unavailable",
        description="All requests return HTTP 503.",
    )

    assert resolution.classification is classification
    assert resolution.solution is solution
    assert knowledge_service.search_for_ticket.await_args.kwargs["classification"] is classification
    assert solution_agent.generate.await_args.kwargs["classification"] is classification
    assert solution_agent.generate.await_args.kwargs["knowledge"] is knowledge
