from unittest.mock import AsyncMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.knowledge_agent import KnowledgeSearchResult
from app.agents.response_agent import ResponseResult
from app.agents.solution_agent import SolutionResult
from app.db.database import Base
from app.db.repositories.review_repository import ReviewRepository
from app.graph.workflow import WorkflowDependencies
from app.llm.structured_output import ClassificationResult, TicketCategory
from app.models.ticket import Ticket
from app.schemas.review import ReviewAction, ReviewActionRequest, ReviewStatus
from app.schemas.ticket import TicketPriority
from app.services.review_service import ReviewService
from app.services.workflow_service import WorkflowExecutionResult, WorkflowExecutionService, WorkflowReviewPause


@pytest.fixture
def workflow_context():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    session.add(Ticket(title="API unavailable", description="HTTP 503"))
    session.commit()
    classification = ClassificationResult(
        category=TicketCategory.TECHNICAL, priority=TicketPriority.URGENT,
        confidence=0.96, reasoning_summary="The API is unavailable."
    )
    knowledge = KnowledgeSearchResult(confidence=0.9, sufficient=True)
    solution = SolutionResult(
        troubleshooting_steps=["Check the status page."], confidence=0.85,
        escalation_required=False, summary="Check platform health."
    )
    response = ResponseResult(
        subject="API availability update", body="Please check the public status page.",
        confidence=0.84, escalation_required=False,
    )
    classifier, knowledge_service = AsyncMock(), AsyncMock()
    solution_agent, response_agent = AsyncMock(), AsyncMock()
    classifier.classify.return_value = classification
    knowledge_service.search_for_ticket.return_value = knowledge
    solution_agent.generate.return_value = solution
    response_agent.generate.return_value = response
    service = WorkflowExecutionService(WorkflowDependencies(
        classifier=classifier, knowledge_service=knowledge_service,
        solution_agent=solution_agent, response_agent=response_agent,
        review_service=ReviewService(ReviewRepository(session)),
    ))
    yield service, solution_agent, response_agent
    session.close()
    engine.dispose()


@pytest.mark.asyncio
async def test_workflow_pauses_and_completes_after_approval(workflow_context) -> None:
    service, solution_agent, response_agent = workflow_context
    paused = await service.start(
        ticket_id=1, title="API unavailable", description="HTTP 503", thread_id="approve-flow"
    )
    assert isinstance(paused, WorkflowReviewPause)
    assert paused.review.status is ReviewStatus.PENDING
    completed = await service.submit_review(
        thread_id=paused.thread_id,
        request=ReviewActionRequest(action=ReviewAction.APPROVE, reviewer="lead@example.com"),
    )
    assert isinstance(completed, WorkflowExecutionResult)
    assert completed.review.status is ReviewStatus.APPROVED
    solution_agent.generate.assert_awaited_once()
    response_agent.generate.assert_awaited_once()


@pytest.mark.asyncio
async def test_rejection_routes_to_rework_and_preserves_state(workflow_context) -> None:
    service, solution_agent, response_agent = workflow_context
    paused = await service.start(
        ticket_id=1, title="API unavailable", description="HTTP 503", thread_id="reject-flow"
    )
    second_pause = await service.submit_review(
        thread_id=paused.thread_id,
        request=ReviewActionRequest(
            action=ReviewAction.REJECT, reviewer="lead@example.com",
            comments="Add regional troubleshooting detail.",
        ),
    )
    assert isinstance(second_pause, WorkflowReviewPause)
    assert second_pause.review.status is ReviewStatus.PENDING
    assert second_pause.review.version == 2
    assert solution_agent.generate.await_count == 2
    assert response_agent.generate.await_count == 2
    assert solution_agent.generate.await_args.kwargs["review_feedback"] == "Add regional troubleshooting detail."
    completed = await service.submit_review(
        thread_id=paused.thread_id,
        request=ReviewActionRequest(action=ReviewAction.APPROVE, reviewer="lead@example.com"),
    )
    assert isinstance(completed, WorkflowExecutionResult)
    assert completed.review.status is ReviewStatus.APPROVED
