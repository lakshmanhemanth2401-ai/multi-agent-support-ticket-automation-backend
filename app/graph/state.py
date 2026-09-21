from typing import NotRequired, TypedDict

from app.agents.knowledge_agent import KnowledgeSearchResult
from app.agents.response_agent import ResponseResult
from app.agents.solution_agent import SolutionResult
from app.llm.structured_output import ClassificationResult
from app.schemas.review import ReviewAction, ReviewRead


class WorkflowInput(TypedDict):
    ticket_id: int
    thread_id: str
    title: str
    description: str


class WorkflowState(WorkflowInput):
    classification: NotRequired[ClassificationResult]
    knowledge: NotRequired[KnowledgeSearchResult]
    solution: NotRequired[SolutionResult]
    response: NotRequired[ResponseResult]
    review: NotRequired[ReviewRead]
    review_action: NotRequired[ReviewAction | None]
    review_comments: NotRequired[str | None]


class WorkflowOutput(TypedDict):
    classification: ClassificationResult
    knowledge: KnowledgeSearchResult
    solution: SolutionResult
    response: ResponseResult
    review: ReviewRead
