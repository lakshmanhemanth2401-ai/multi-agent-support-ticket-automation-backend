from app.agents.knowledge_agent import KnowledgeSearchAgent, KnowledgeSearchResult
from app.llm.structured_output import ClassificationResult


class KnowledgeService:
    def __init__(self, agent: KnowledgeSearchAgent | None = None) -> None:
        self.agent = agent or KnowledgeSearchAgent()

    async def search_for_ticket(
        self,
        *,
        title: str,
        description: str,
        classification: ClassificationResult,
    ) -> KnowledgeSearchResult:
        return await self.agent.search(
            title=title,
            description=description,
            classification=classification,
        )
