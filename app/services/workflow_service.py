from dataclasses import dataclass
from typing import Any

from app.agents.knowledge_agent import KnowledgeSearchResult
from app.agents.response_agent import ResponseResult
from app.agents.solution_agent import SolutionResult
from app.graph.workflow import WorkflowDependencies, build_support_workflow
from app.llm.structured_output import ClassificationResult
from app.schemas.review import ReviewActionRequest, ReviewRead
from langgraph.types import Command
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class WorkflowExecutionResult:
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
        self.workflow = workflow or build_support_workflow(dependencies)

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
        await self.workflow.ainvoke(
            {"ticket_id": ticket_id, "thread_id": resolved_thread_id, "title": title, "description": description},
            config,
        )
        state = self.workflow.get_state(config).values
        return WorkflowReviewPause(
            thread_id=resolved_thread_id,
            review=state["review"],
            response=state["response"],
        )

    async def submit_review(
        self, *, thread_id: str, request: ReviewActionRequest
    ) -> WorkflowReviewPause | WorkflowExecutionResult:
        config = {"configurable": {"thread_id": thread_id}}
        await self.workflow.ainvoke(Command(resume=request.model_dump(mode="json")), config)
        snapshot = self.workflow.get_state(config)
        state = snapshot.values
        if snapshot.next:
            return WorkflowReviewPause(
                thread_id=thread_id, review=state["review"], response=state["response"]
            )
        return WorkflowExecutionResult(
            classification=state["classification"],
            knowledge=state["knowledge"],
            solution=state["solution"],
            response=state["response"],
            review=state["review"],
        )
