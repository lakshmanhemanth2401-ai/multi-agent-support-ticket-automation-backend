import logging
from dataclasses import dataclass, field

from app.agents.base import BaseAgent
from app.agents.knowledge_agent import KnowledgeSearchResult
from app.agents.solution_agent import SolutionResult, SupportingSource
from app.llm.ollama_client import OllamaClient, OllamaError
from app.llm.prompts import build_response_messages
from app.llm.structured_output import (
    ClassificationResult,
    ProfessionalResponseDraft,
    StructuredOutputError,
    parse_structured_output,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ResponseInput:
    title: str
    description: str
    classification: ClassificationResult
    knowledge: KnowledgeSearchResult
    solution: SolutionResult


@dataclass(frozen=True, slots=True)
class ResponseResult:
    subject: str
    body: str
    confidence: float
    escalation_required: bool
    supporting_sources: list[SupportingSource] = field(default_factory=list)


class ResponseAgent(BaseAgent[ResponseInput, ResponseResult]):
    def __init__(self, client: OllamaClient | None = None) -> None:
        self.client = client or OllamaClient()

    async def run(self, agent_input: ResponseInput) -> ResponseResult:
        schema = ProfessionalResponseDraft.model_json_schema()
        messages = build_response_messages(
            title=agent_input.title,
            description=agent_input.description,
            category=agent_input.classification.category.value,
            priority=agent_input.classification.priority.value,
            troubleshooting_steps=agent_input.solution.troubleshooting_steps,
            solution_summary=agent_input.solution.summary,
            escalation_required=agent_input.solution.escalation_required,
            escalation_reason=agent_input.solution.escalation_reason,
            evidence=[
                {"source": result.source, "content": result.content}
                for result in agent_input.knowledge.results
            ],
            output_schema=schema,
        )
        try:
            content = await self.client.chat(messages=messages, output_schema=schema)
            draft = parse_structured_output(content, ProfessionalResponseDraft)
        except (OllamaError, StructuredOutputError):
            logger.exception("Professional response generation failed")
            return self._fallback(agent_input)

        return ResponseResult(
            subject=draft.subject,
            body=draft.body,
            confidence=min(draft.confidence, agent_input.solution.confidence),
            escalation_required=agent_input.solution.escalation_required,
            supporting_sources=agent_input.solution.supporting_sources,
        )

    async def generate(
        self,
        *,
        title: str,
        description: str,
        classification: ClassificationResult,
        knowledge: KnowledgeSearchResult,
        solution: SolutionResult,
    ) -> ResponseResult:
        return await self.run(
            ResponseInput(
                title=title,
                description=description,
                classification=classification,
                knowledge=knowledge,
                solution=solution,
            )
        )

    @staticmethod
    def _fallback(agent_input: ResponseInput) -> ResponseResult:
        return ResponseResult(
            subject=f"Update on your support request: {agent_input.title}",
            body=(
                "Thank you for contacting support. We have reviewed your request, but "
                "we are unable to generate a sufficiently reliable automated response. "
                "A support specialist will review the case and follow up with verified "
                "next steps."
            ),
            confidence=0.0,
            escalation_required=True,
            supporting_sources=agent_input.solution.supporting_sources,
        )
