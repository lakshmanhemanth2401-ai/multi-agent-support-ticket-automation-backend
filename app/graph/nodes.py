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


WorkflowNode = Callable[[WorkflowState], Awaitable[dict[str, Any]]]


def create_classifier_node(agent: ClassifierAgent) -> WorkflowNode:
    async def classify(state: WorkflowState) -> dict[str, Any]:
        result = await agent.classify(
            title=state["title"], description=state["description"]
        )
        return {"classification": result}

    return classify


def create_knowledge_node(service: KnowledgeService) -> WorkflowNode:
    async def search(state: WorkflowState) -> dict[str, Any]:
        result = await service.search_for_ticket(
            title=state["title"],
            description=state["description"],
            classification=state["classification"],
        )
        return {"knowledge": result}

    return search


def create_solution_node(agent: SolutionAgent) -> WorkflowNode:
    async def solve(state: WorkflowState) -> dict[str, Any]:
        result = await agent.generate(
            title=state["title"],
            description=state["description"],
            classification=state["classification"],
            knowledge=state["knowledge"],
            review_feedback=state.get("review_comments"),
        )
        return {"solution": result}

    return solve


def create_response_node(agent: ResponseAgent) -> WorkflowNode:
    async def respond(state: WorkflowState) -> dict[str, Any]:
        result = await agent.generate(
            title=state["title"],
            description=state["description"],
            classification=state["classification"],
            knowledge=state["knowledge"],
            solution=state["solution"],
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
