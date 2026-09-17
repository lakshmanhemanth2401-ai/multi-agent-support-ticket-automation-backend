import logging
from dataclasses import dataclass, field

from app.agents.base import BaseAgent
from app.agents.knowledge_agent import KnowledgeSearchResult
from app.core.config import settings
from app.llm.ollama_client import OllamaClient, OllamaError
from app.llm.prompts import build_solution_messages
from app.llm.structured_output import (
    ClassificationResult,
    StructuredOutputError,
    TroubleshootingPlan,
    parse_structured_output,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SupportingSource:
    source: str
    title: str | None
    relevance_score: float


@dataclass(frozen=True, slots=True)
class SolutionInput:
    title: str
    description: str
    classification: ClassificationResult
    knowledge: KnowledgeSearchResult


@dataclass(frozen=True, slots=True)
class SolutionResult:
    troubleshooting_steps: list[str] = field(default_factory=list)
    confidence: float = 0.0
    supporting_sources: list[SupportingSource] = field(default_factory=list)
    escalation_required: bool = True
    escalation_reason: str | None = None
    summary: str = ""


class SolutionAgent(BaseAgent[SolutionInput, SolutionResult]):
    def __init__(
        self,
        client: OllamaClient | None = None,
        *,
        minimum_confidence: float = settings.solution_min_confidence,
    ) -> None:
        self.client = client or OllamaClient()
        self.minimum_confidence = minimum_confidence

    async def run(self, agent_input: SolutionInput) -> SolutionResult:
        sources = self._supporting_sources(agent_input.knowledge)
        if not agent_input.knowledge.sufficient:
            return self._escalation(
                reason=agent_input.knowledge.reason
                or "Knowledge is insufficient for a safe recommendation.",
                sources=sources,
            )

        schema = TroubleshootingPlan.model_json_schema()
        messages = build_solution_messages(
            title=agent_input.title,
            description=agent_input.description,
            category=agent_input.classification.category.value,
            priority=agent_input.classification.priority.value,
            evidence=[
                {"source": result.source, "content": result.content}
                for result in agent_input.knowledge.results
            ],
            output_schema=schema,
        )
        try:
            content = await self.client.chat(messages=messages, output_schema=schema)
            plan = parse_structured_output(content, TroubleshootingPlan)
        except (OllamaError, StructuredOutputError):
            logger.exception("Solution generation failed")
            return self._escalation(
                reason="Automated solution generation failed; human review required.",
                sources=sources,
            )

        confidence = min(plan.confidence, agent_input.knowledge.confidence)
        escalation_required = confidence < self.minimum_confidence
        return SolutionResult(
            troubleshooting_steps=plan.troubleshooting_steps,
            confidence=confidence,
            supporting_sources=sources,
            escalation_required=escalation_required,
            escalation_reason=(
                "Solution confidence is below the required threshold."
                if escalation_required
                else None
            ),
            summary=plan.summary,
        )

    async def generate(
        self,
        *,
        title: str,
        description: str,
        classification: ClassificationResult,
        knowledge: KnowledgeSearchResult,
    ) -> SolutionResult:
        return await self.run(
            SolutionInput(
                title=title,
                description=description,
                classification=classification,
                knowledge=knowledge,
            )
        )

    @staticmethod
    def _supporting_sources(
        knowledge: KnowledgeSearchResult,
    ) -> list[SupportingSource]:
        sources: list[SupportingSource] = []
        seen: set[str] = set()
        for result in knowledge.results:
            if result.source in seen:
                continue
            seen.add(result.source)
            title = result.metadata.get("title")
            sources.append(
                SupportingSource(
                    source=result.source,
                    title=str(title) if title else None,
                    relevance_score=result.relevance_score,
                )
            )
        return sources

    @staticmethod
    def _escalation(
        *, reason: str, sources: list[SupportingSource]
    ) -> SolutionResult:
        return SolutionResult(
            supporting_sources=sources,
            escalation_required=True,
            escalation_reason=reason,
            summary="Human support review is required before recommending next steps.",
        )
