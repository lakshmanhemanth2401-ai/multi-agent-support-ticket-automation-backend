from collections.abc import Awaitable, Callable
from typing import Any

from app.agents.classifier_agent import ClassifierAgent
from app.agents.response_agent import ResponseAgent
from app.agents.solution_agent import SolutionAgent
from app.graph.state import WorkflowState
from app.services.knowledge_service import KnowledgeService
from app.services.review_service import ReviewService
from app.schemas.review import ReviewAction, ReviewActionRequest
from app.agents.response_agent import ResponseResult
from langgraph.types import interrupt
import logging

from app.observability.metrics import AGENT_EXECUTIONS, AGENT_FAILURES
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


WorkflowNode = Callable[[WorkflowState], Awaitable[dict[str, Any]]]


async def _run_agent(*, name: str, ticket_id: int, operation, audit: AuditService | None, details):
    logger.info("agent_started", extra={"event": "agent_transition", "agent": name, "ticket_id": ticket_id, "status": "started"})
    try:
        result = await operation()
    except Exception as exc:
        AGENT_EXECUTIONS.labels(name, "failure").inc()
        AGENT_FAILURES.labels(name, type(exc).__name__).inc()
        if audit:
            audit.record_agent_event(ticket_id=ticket_id, agent=name, status="failed", details={"error_type": type(exc).__name__})
        logger.exception("agent_failed", extra={"event": "agent_transition", "agent": name, "ticket_id": ticket_id, "status": "failed"})
        raise
    AGENT_EXECUTIONS.labels(name, "success").inc()
    if audit:
        audit.record_agent_event(ticket_id=ticket_id, agent=name, status="completed", details=details(result))
    logger.info("agent_completed", extra={"event": "agent_transition", "agent": name, "ticket_id": ticket_id, "status": "completed"})
    return result


def create_classifier_node(agent: ClassifierAgent, audit: AuditService | None = None) -> WorkflowNode:
    async def classify(state: WorkflowState) -> dict[str, Any]:
        result = await _run_agent(
            name="classifier", ticket_id=state["ticket_id"], audit=audit,
            operation=lambda: agent.classify(title=state["title"], description=state["description"]),
            details=lambda value: {"category": value.category, "priority": value.priority, "confidence": value.confidence},
        )
        return {"classification": result}

    return classify


def create_knowledge_node(service: KnowledgeService, audit: AuditService | None = None) -> WorkflowNode:
    async def search(state: WorkflowState) -> dict[str, Any]:
        result = await _run_agent(
            name="retrieval", ticket_id=state["ticket_id"], audit=audit,
            operation=lambda: service.search_for_ticket(title=state["title"], description=state["description"], classification=state["classification"]),
            details=lambda value: {"result_count": len(value.results), "confidence": value.confidence, "knowledge_sufficient": value.sufficient},
        )
        return {"knowledge": result}

    return search


def create_solution_node(agent: SolutionAgent, audit: AuditService | None = None) -> WorkflowNode:
    async def solve(state: WorkflowState) -> dict[str, Any]:
        result = await _run_agent(
            name="solution", ticket_id=state["ticket_id"], audit=audit,
            operation=lambda: agent.generate(title=state["title"], description=state["description"], classification=state["classification"], knowledge=state["knowledge"], review_feedback=state.get("review_comments")),
            details=lambda value: {"confidence": value.confidence, "escalation_required": value.escalation_required, "source_count": len(value.supporting_sources)},
        )
        return {"solution": result}

    return solve


def create_response_node(agent: ResponseAgent, audit: AuditService | None = None) -> WorkflowNode:
    async def respond(state: WorkflowState) -> dict[str, Any]:
        result = await _run_agent(
            name="response", ticket_id=state["ticket_id"], audit=audit,
            operation=lambda: agent.generate(title=state["title"], description=state["description"], classification=state["classification"], knowledge=state["knowledge"], solution=state["solution"]),
            details=lambda value: {"confidence": value.confidence, "escalation_required": value.escalation_required, "source_count": len(value.supporting_sources)},
        )
        return {"response": result}

    return respond


def create_review_record_node(service: ReviewService) -> WorkflowNode:
    async def persist(state: WorkflowState) -> dict[str, Any]:
        existing = state.get("review")
        if existing is None:
            review = service.create_pending(
                ticket_id=state["ticket_id"],
                thread_id=state["thread_id"],
                response=state["response"],
            )
        else:
            review = service.mark_reworked(existing.id, state["response"])
        return {"review": review, "review_action": None, "review_comments": None}

    return persist


def create_human_review_node(service: ReviewService) -> WorkflowNode:
    async def review(state: WorkflowState) -> dict[str, Any]:
        current = state["review"]
        payload = interrupt(
            {
                "review_id": current.id,
                "ticket_id": current.ticket_id,
                "subject": current.generated_subject,
                "response": current.generated_response,
                "version": current.version,
                "allowed_actions": [action.value for action in ReviewAction],
            }
        )
        request = ReviewActionRequest.model_validate(payload)
        updated = service.apply_action(current.id, request)
        update: dict[str, Any] = {
            "review": updated,
            "review_action": request.action,
            "review_comments": request.comments,
        }
        if request.action is ReviewAction.EDIT:
            prior = state["response"]
            update["response"] = ResponseResult(
                subject=request.edited_subject or prior.subject,
                body=request.edited_response or prior.body,
                confidence=prior.confidence,
                escalation_required=False,
                supporting_sources=prior.supporting_sources,
            )
        return update

    return review
