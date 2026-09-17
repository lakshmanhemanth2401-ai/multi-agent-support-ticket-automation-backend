from dataclasses import dataclass

from app.agents.classifier_agent import ClassifierAgent
from app.agents.solution_agent import SolutionAgent, SolutionResult
from app.llm.structured_output import ClassificationResult
from app.services.knowledge_service import KnowledgeService


@dataclass(frozen=True, slots=True)
class TicketResolution:
    classification: ClassificationResult
    solution: SolutionResult


class AgentService:
    """Orchestrate ticket classification, knowledge search, and resolution."""

    def __init__(
        self,
        *,
        classifier: ClassifierAgent | None = None,
        knowledge_service: KnowledgeService | None = None,
        solution_agent: SolutionAgent | None = None,
    ) -> None:
        self.classifier = classifier or ClassifierAgent()
        self.knowledge_service = knowledge_service or KnowledgeService()
        self.solution_agent = solution_agent or SolutionAgent()

    async def resolve_ticket(self, *, title: str, description: str) -> TicketResolution:
        classification = await self.classifier.classify(
            title=title, description=description
        )
        knowledge = await self.knowledge_service.search_for_ticket(
            title=title,
            description=description,
            classification=classification,
        )
        solution = await self.solution_agent.generate(
            title=title,
            description=description,
            classification=classification,
            knowledge=knowledge,
        )
        return TicketResolution(classification=classification, solution=solution)
