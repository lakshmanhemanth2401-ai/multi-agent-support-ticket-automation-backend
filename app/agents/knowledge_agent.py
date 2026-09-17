import logging
from dataclasses import dataclass, field

from app.agents.base import BaseAgent
from app.core.config import settings
from app.llm.structured_output import ClassificationResult
from app.rag.retriever import KnowledgeRetriever
from app.rag.vector_store import RetrievalResult


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class KnowledgeSearchInput:
    title: str
    description: str
    classification: ClassificationResult
    top_k: int = settings.knowledge_top_k


@dataclass(frozen=True, slots=True)
class KnowledgeSearchResult:
    results: list[RetrievalResult] = field(default_factory=list)
    confidence: float = 0.0
    sufficient: bool = False
    reason: str | None = None
    query: str = ""


class KnowledgeSearchAgent(
    BaseAgent[KnowledgeSearchInput, KnowledgeSearchResult]
):
    def __init__(
        self,
        retriever: KnowledgeRetriever | None = None,
        *,
        minimum_relevance: float = settings.knowledge_min_relevance,
    ) -> None:
        self.retriever = retriever or KnowledgeRetriever()
        self.minimum_relevance = minimum_relevance

    async def run(self, agent_input: KnowledgeSearchInput) -> KnowledgeSearchResult:
        query = self._build_query(agent_input)
        try:
            results = self.retriever.retrieve(query, top_k=agent_input.top_k)
        except Exception:
            logger.exception("Knowledge retrieval failed")
            return KnowledgeSearchResult(
                reason="Knowledge retrieval failed; human escalation required.",
                query=query,
            )

        confidence = max((result.relevance_score for result in results), default=0.0)
        sufficient = bool(results) and confidence >= self.minimum_relevance
        reason = None
        if not results:
            reason = "No supporting knowledge was found."
        elif not sufficient:
            reason = "Retrieved knowledge relevance is below the required threshold."
        return KnowledgeSearchResult(
            results=results,
            confidence=confidence,
            sufficient=sufficient,
            reason=reason,
            query=query,
        )

    async def search(
        self,
        *,
        title: str,
        description: str,
        classification: ClassificationResult,
        top_k: int = settings.knowledge_top_k,
    ) -> KnowledgeSearchResult:
        return await self.run(
            KnowledgeSearchInput(
                title=title,
                description=description,
                classification=classification,
                top_k=top_k,
            )
        )

    @staticmethod
    def _build_query(agent_input: KnowledgeSearchInput) -> str:
        classification = agent_input.classification
        return (
            f"Support category: {classification.category.value}. "
            f"Priority: {classification.priority.value}. "
            f"Ticket: {agent_input.title}. {agent_input.description}"
        )
