from enum import StrEnum

from pydantic import BaseModel

from app.llm.structured_output import TicketCategory
from app.schemas.review import ReviewRead
from app.schemas.ticket import TicketPriority
from pydantic import Field


class ClassificationRead(BaseModel):
    category: TicketCategory
    priority: TicketPriority
    confidence: float = Field(ge=0.0, le=1.0)


class RetrievedKnowledgeRead(BaseModel):
    content: str
    source: str
    metadata: dict[str, object] = Field(default_factory=dict)
    relevance_score: float = Field(ge=0.0, le=1.0)


class KnowledgeContextRead(BaseModel):
    chunks: list[RetrievedKnowledgeRead]
    confidence: float = Field(ge=0.0, le=1.0)
    sufficient: bool


class SupportingSourceRead(BaseModel):
    source: str
    title: str | None
    relevance_score: float = Field(ge=0.0, le=1.0)


class SolutionRead(BaseModel):
    summary: str
    troubleshooting_steps: list[str]
    supporting_sources: list[SupportingSourceRead]
    confidence: float = Field(ge=0.0, le=1.0)
    escalation_required: bool
    escalation_reason: str | None


class GeneratedResponseRead(BaseModel):
    subject: str
    body: str
    confidence: float = Field(ge=0.0, le=1.0)
    escalation_required: bool
    supporting_sources: list[SupportingSourceRead]


class WorkflowStatus(StrEnum):
    AWAITING_REVIEW = "awaiting_review"
    COMPLETED = "completed"


class WorkflowRead(BaseModel):
    thread_id: str
    status: WorkflowStatus
    review: ReviewRead
    classification: ClassificationRead
    knowledge: KnowledgeContextRead
    solution: SolutionRead
    generated_response: GeneratedResponseRead
    confidence: float = Field(ge=0.0, le=1.0)
    escalation_required: bool
