from enum import StrEnum
from typing import TypeVar

from pydantic import BaseModel, Field, ValidationError

from app.schemas.ticket import TicketPriority


class TicketCategory(StrEnum):
    ACCOUNT = "account"
    BILLING = "billing"
    PRODUCT = "product"
    SECURITY = "security"
    TECHNICAL = "technical"
    GENERAL = "general"


class ClassificationResult(BaseModel):
    category: TicketCategory
    priority: TicketPriority
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning_summary: str = Field(min_length=1, max_length=500)


class TroubleshootingPlan(BaseModel):
    troubleshooting_steps: list[str] = Field(min_length=1, max_length=8)
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(min_length=1, max_length=500)


class ProfessionalResponseDraft(BaseModel):
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=4_000)
    confidence: float = Field(ge=0.0, le=1.0)


class StructuredOutputError(ValueError):
    """Raised when an LLM response does not match the expected schema."""


StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


def parse_structured_output(
    content: str, model_type: type[StructuredModel]
) -> StructuredModel:
    try:
        return model_type.model_validate_json(content)
    except ValidationError as exc:
        raise StructuredOutputError("Ollama returned invalid structured output") from exc
