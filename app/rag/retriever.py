from app.rag.vector_store import ChromaVectorStore, RetrievalResult


class KnowledgeRetriever:
    def __init__(self, vector_store: ChromaVectorStore | None = None) -> None:
        self.vector_store = vector_store or ChromaVectorStore()

    def retrieve(self, query: str, *, top_k: int = 5) -> list[RetrievalResult]:
        """Return the most relevant support chunks and their source metadata."""

        return self.vector_store.semantic_search(query, top_k=top_k)
