from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.pagination import PageMetadata


class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketAnalysisStatus(StrEnum):
    NOT_STARTED = "not_started"
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_REVIEW = "awaiting_review"
    COMPLETED = "completed"
    FAILED = "failed"


class TicketCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10_000)
    priority: TicketPriority = TicketPriority.MEDIUM
    category: str | None = Field(
        default=None, min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9 _-]+$"
    )

    @field_validator("category", mode="before")
    @classmethod
    def normalize_empty_category(cls, value: object) -> object:
        return None if isinstance(value, str) and not value.strip() else value


class TicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    category: str | None
    workflow_thread_id: str | None
    analysis_status: TicketAnalysisStatus
    analysis_error: str | None
    created_at: datetime
    updated_at: datetime


class TicketPage(BaseModel):
    items: list[TicketRead]
    pagination: PageMetadata
