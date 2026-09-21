from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EDITED = "edited"
    REGENERATE_REQUESTED = "regenerate_requested"


class ReviewAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    EDIT = "edit"
    REGENERATE = "regenerate"


class ReviewCreate(BaseModel):
    ticket_id: int
    workflow_thread_id: str = Field(min_length=1, max_length=100)
    generated_subject: str = Field(min_length=1, max_length=200)
    generated_response: str = Field(min_length=1)


class ReviewActionRequest(BaseModel):
    action: ReviewAction
    reviewer: str = Field(min_length=1, max_length=150)
    comments: str | None = None
    edited_subject: str | None = Field(default=None, max_length=200)
    edited_response: str | None = None

    @model_validator(mode="after")
    def validate_action_fields(self) -> "ReviewActionRequest":
        if self.action in {ReviewAction.REJECT, ReviewAction.REGENERATE} and not self.comments:
            raise ValueError("comments are required for reject and regenerate actions")
        if self.action is ReviewAction.EDIT and not self.edited_response:
            raise ValueError("edited_response is required for edit actions")
        return self


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    workflow_thread_id: str | None
    generated_subject: str | None
    generated_response: str | None
    status: ReviewStatus
    reviewer: str | None
    reviewer_comments: str | None
    edited_subject: str | None
    edited_response: str | None
    version: int
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None
