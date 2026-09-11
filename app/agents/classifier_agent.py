import logging
from dataclasses import dataclass

from app.agents.base import BaseAgent
from app.llm.ollama_client import OllamaClient, OllamaError
from app.llm.prompts import build_classifier_messages
from app.llm.structured_output import (
    ClassificationResult,
    StructuredOutputError,
    TicketCategory,
    parse_structured_output,
)
from app.schemas.ticket import TicketPriority


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TicketClassificationInput:
    title: str
    description: str


class ClassifierAgent(
    BaseAgent[TicketClassificationInput, ClassificationResult]
):
    def __init__(self, client: OllamaClient | None = None) -> None:
        self.client = client or OllamaClient()

    async def run(
        self, agent_input: TicketClassificationInput
    ) -> ClassificationResult:
        schema = ClassificationResult.model_json_schema()
        messages = build_classifier_messages(
            title=agent_input.title,
            description=agent_input.description,
            output_schema=schema,
        )

        try:
            content = await self.client.chat(
                messages=messages,
                output_schema=schema,
            )
            return parse_structured_output(content, ClassificationResult)
        except (OllamaError, StructuredOutputError):
            logger.exception("Ticket classification failed; using manual-triage fallback")
            return ClassificationResult(
                category=TicketCategory.GENERAL,
                priority=TicketPriority.MEDIUM,
                confidence=0.0,
                reasoning_summary=(
                    "Automated classification unavailable; manual triage required."
                ),
            )

    async def classify(
        self, *, title: str, description: str
    ) -> ClassificationResult:
        return await self.run(
            TicketClassificationInput(title=title, description=description)
        )
