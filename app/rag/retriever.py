from app.rag.vector_store import ChromaVectorStore, RetrievalResult
from app.core.config import settings
from app.core.retry import retry_sync
from app.observability.metrics import RETRIEVAL_LATENCY
from time import perf_counter


class RetrievalError(RuntimeError):
    """Raised when ChromaDB retrieval remains unavailable after retries."""


class KnowledgeRetriever:
    def __init__(self, vector_store: ChromaVectorStore | None = None) -> None:
        self.vector_store = vector_store or ChromaVectorStore()

    def retrieve(self, query: str, *, top_k: int = 5) -> list[RetrievalResult]:
        """Return the most relevant support chunks and their source metadata."""

        started = perf_counter()
        status = "success"
        try:
            return retry_sync(
                lambda: self.vector_store.semantic_search(query, top_k=top_k),
                attempts=settings.retry_max_attempts,
                base_delay=settings.retry_base_delay_seconds,
                retry_for=(RuntimeError, TimeoutError, ConnectionError),
            )
        except (RuntimeError, TimeoutError, ConnectionError) as exc:
            status = "failure"
            raise RetrievalError("Knowledge retrieval is temporarily unavailable") from exc
        finally:
            RETRIEVAL_LATENCY.labels(status).observe(perf_counter() - started)
