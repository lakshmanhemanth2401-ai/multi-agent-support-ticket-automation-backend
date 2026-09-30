from app.db.repositories.knowledge_repository import KnowledgeRepository
from app.rag.retriever import KnowledgeRetriever
from app.schemas.knowledge import (
    KnowledgeDocumentPage,
    KnowledgeSearchResponse,
    KnowledgeSearchResultRead,
)
from app.schemas.pagination import PageMetadata
from app.core.errors import DependencyUnavailableError
from app.rag.retriever import RetrievalError


class KnowledgeCatalogService:
    def __init__(
        self,
        repository: KnowledgeRepository,
        retriever: KnowledgeRetriever | None = None,
    ) -> None:
        self.repository = repository
        self.retriever = retriever or KnowledgeRetriever()

    def list_documents(self, *, offset: int, limit: int) -> KnowledgeDocumentPage:
        items, total = self.repository.list_documents(offset=offset, limit=limit)
        return KnowledgeDocumentPage(
            items=items,
            pagination=PageMetadata(offset=offset, limit=limit, total=total),
        )

    def search(self, *, query: str, top_k: int) -> KnowledgeSearchResponse:
        try:
            results = self.retriever.retrieve(query, top_k=top_k)
        except RetrievalError as exc:
            raise DependencyUnavailableError() from exc
        items = [
            KnowledgeSearchResultRead(
                content=result.content,
                source=result.source,
                metadata=result.metadata,
                relevance_score=max(0.0, min(1.0, result.relevance_score)),
            )
            for result in results
        ]
        return KnowledgeSearchResponse(items=items, count=len(items))
