from enum import StrEnum

from pydantic import BaseModel

from app.agents.knowledge_agent import KnowledgeSearchResult
from app.agents.response_agent import ResponseResult
from app.agents.solution_agent import SolutionResult
from app.llm.structured_output import ClassificationResult
from app.schemas.review import ReviewRead


class WorkflowStatus(StrEnum):
    AWAITING_REVIEW = "awaiting_review"
    COMPLETED = "completed"


class WorkflowRead(BaseModel):
    thread_id: str
    status: WorkflowStatus
    review: ReviewRead
    response: ResponseResult
    classification: ClassificationResult | None = None
    knowledge: KnowledgeSearchResult | None = None
    solution: SolutionResult | None = None
