from dataclasses import dataclass
from typing import Any

from app.agents.knowledge_agent import KnowledgeSearchResult
from app.agents.response_agent import ResponseResult
from app.agents.solution_agent import SolutionResult
from app.graph.workflow import WorkflowDependencies, build_support_workflow, default_workflow_dependencies
from app.llm.structured_output import ClassificationResult
from app.schemas.review import ReviewActionRequest, ReviewRead
from langgraph.types import Command
from uuid import uuid4
from time import perf_counter
import logging

from app.observability.metrics import TICKETS_PROCESSED, WORKFLOW_DURATION

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class WorkflowExecutionResult:
    thread_id: str
    classification: ClassificationResult
    knowledge: KnowledgeSearchResult
    solution: SolutionResult
    response: ResponseResult
    review: ReviewRead


@dataclass(frozen=True, slots=True)
class WorkflowReviewPause:
    thread_id: str
    review: ReviewRead
    response: ResponseResult


class WorkflowExecutionService:
    def __init__(
        self,
        dependencies: WorkflowDependencies | None = None,
        *,
        workflow: Any | None = None,
    ) -> None:
        resolved_dependencies = dependencies
        if workflow is None and resolved_dependencies is None:
            resolved_dependencies = default_workflow_dependencies()
        self.dependencies = resolved_dependencies
        self.workflow = workflow or build_support_workflow(resolved_dependencies)

    def _record_failure(self, ticket_id: int, stage: str, exc: Exception) -> None:
        if self.dependencies and self.dependencies.audit_service:
            self.dependencies.audit_service.record_workflow_failure(ticket_id=ticket_id, stage=stage, error=exc)
        logger.exception("workflow_failed", extra={"event": "workflow_failure", "ticket_id": ticket_id, "stage": stage, "status": "failed"})

    async def execute(
        self, *, ticket_id: int, title: str, description: str, thread_id: str | None = None
    ) -> WorkflowReviewPause:
        return await self.start(
            ticket_id=ticket_id, title=title, description=description, thread_id=thread_id
        )

    async def start(
        self, *, ticket_id: int, title: str, description: str, thread_id: str | None = None
    ) -> WorkflowReviewPause:
        resolved_thread_id = thread_id or str(uuid4())
        config = {"configurable": {"thread_id": resolved_thread_id}}
        started = perf_counter()
        try:
            await self.workflow.ainvoke(
                {"ticket_id": ticket_id, "thread_id": resolved_thread_id, "title": title, "description": description}, config,
            )
            WORKFLOW_DURATION.labels("awaiting_review").observe(perf_counter() - started)
        except Exception as exc:
            WORKFLOW_DURATION.labels("failure").observe(perf_counter() - started)
            TICKETS_PROCESSED.labels("failure").inc()
            self._record_failure(ticket_id, "execution", exc)
            raise
        state = (await self.workflow.aget_state(config)).values
        return WorkflowReviewPause(
            thread_id=resolved_thread_id,
            review=state["review"],
            response=state["response"],
        )

    async def submit_review(
        self, *, thread_id: str, request: ReviewActionRequest
    ) -> WorkflowReviewPause | WorkflowExecutionResult:
        config = {"configurable": {"thread_id": thread_id}}
        started = perf_counter()
        try:
            await self.workflow.ainvoke(Command(resume=request.model_dump(mode="json")), config)
        except Exception as exc:
            WORKFLOW_DURATION.labels("failure").observe(perf_counter() - started)
            snapshot = await self.workflow.aget_state(config)
            ticket_id = snapshot.values.get("ticket_id")
            if ticket_id is not None:
                self._record_failure(ticket_id, "review", exc)
            logger.exception("workflow_review_failed", extra={"event": "workflow_failure", "stage": "review", "status": "failed"})
            raise
        snapshot = await self.workflow.aget_state(config)
        state = snapshot.values
        if snapshot.next:
            WORKFLOW_DURATION.labels("awaiting_review").observe(perf_counter() - started)
            return WorkflowReviewPause(
                thread_id=thread_id, review=state["review"], response=state["response"]
            )
        WORKFLOW_DURATION.labels("completed").observe(perf_counter() - started)
        TICKETS_PROCESSED.labels("success").inc()
        return WorkflowExecutionResult(
            thread_id=thread_id,
            classification=state["classification"],
            knowledge=state["knowledge"],
            solution=state["solution"],
            response=state["response"],
            review=state["review"],
        )

    async def get_status(self, *, thread_id: str) -> WorkflowReviewPause | WorkflowExecutionResult:
        config = {"configurable": {"thread_id": thread_id}}
        snapshot = await self.workflow.aget_state(config)
        state = snapshot.values
        if not state or "review" not in state or "response" not in state:
            raise LookupError(f"Workflow {thread_id} was not found")
        if snapshot.next:
            return WorkflowReviewPause(
                thread_id=thread_id, review=state["review"], response=state["response"]
            )
        return WorkflowExecutionResult(
            thread_id=thread_id,
            classification=state["classification"],
            knowledge=state["knowledge"],
            solution=state["solution"],
            response=state["response"],
            review=state["review"],
        )
