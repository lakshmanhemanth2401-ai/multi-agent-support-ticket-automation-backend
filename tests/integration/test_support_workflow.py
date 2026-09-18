from unittest.mock import AsyncMock

import pytest

from app.agents.knowledge_agent import KnowledgeSearchResult
from app.agents.response_agent import ResponseResult
from app.agents.solution_agent import SolutionResult, SupportingSource
from app.graph.workflow import WorkflowDependencies
from app.llm.structured_output import ClassificationResult, TicketCategory
from app.rag.vector_store import RetrievalResult
from app.schemas.ticket import TicketPriority
from app.services.workflow_service import WorkflowExecutionService


@pytest.mark.asyncio
async def test_workflow_executes_all_agents_in_order_with_context_handoff() -> None:
    calls: list[str] = []
    classification = ClassificationResult(
        category=TicketCategory.TECHNICAL,
        priority=TicketPriority.URGENT,
        confidence=0.96,
        reasoning_summary="Multiple regions return HTTP 503.",
    )
    knowledge = KnowledgeSearchResult(
        results=[
            RetrievalResult(
                content="Check regional error rate and the public status page.",
                source="platform/api_incident.md",
                relevance_score=0.92,
                distance=0.08,
                metadata={"title": "API Incident Runbook"},
            )
        ],
        confidence=0.92,
        sufficient=True,
        query="urgent technical API outage",
    )
    sources = [
        SupportingSource(
            source="platform/api_incident.md",
            title="API Incident Runbook",
            relevance_score=0.92,
        )
    ]
    solution = SolutionResult(
        troubleshooting_steps=["Check the public status page."],
        confidence=0.88,
        supporting_sources=sources,
        escalation_required=False,
        summary="Confirm platform health before integration changes.",
    )
    response = ResponseResult(
        subject="API availability investigation",
        body="We are reviewing the reported API errors. Please check the status page.",
        confidence=0.86,
        escalation_required=False,
        supporting_sources=sources,
    )

    classifier = AsyncMock()
    knowledge_service = AsyncMock()
    solution_agent = AsyncMock()
    response_agent = AsyncMock()

    async def classify(**_: object) -> ClassificationResult:
        calls.append("classifier")
        return classification

    async def search(**kwargs: object) -> KnowledgeSearchResult:
        calls.append("knowledge")
        assert kwargs["classification"] is classification
        return knowledge

    async def solve(**kwargs: object) -> SolutionResult:
        calls.append("solution")
        assert kwargs["classification"] is classification
        assert kwargs["knowledge"] is knowledge
        return solution

    async def respond(**kwargs: object) -> ResponseResult:
        calls.append("response")
        assert kwargs["classification"] is classification
        assert kwargs["knowledge"] is knowledge
        assert kwargs["solution"] is solution
        return response

    classifier.classify.side_effect = classify
    knowledge_service.search_for_ticket.side_effect = search
    solution_agent.generate.side_effect = solve
    response_agent.generate.side_effect = respond
    dependencies = WorkflowDependencies(
        classifier=classifier,
        knowledge_service=knowledge_service,
        solution_agent=solution_agent,
        response_agent=response_agent,
    )
    service = WorkflowExecutionService(dependencies)

    result = await service.execute(
        title="API unavailable",
        description="Requests in two regions return HTTP 503.",
    )

    assert calls == ["classifier", "knowledge", "solution", "response"]
    assert result.classification is classification
    assert result.knowledge is knowledge
    assert result.solution is solution
    assert result.response is response
