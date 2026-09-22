from collections.abc import Sequence

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.core.retry import retry_sync
from app.observability.metrics import LLM_LATENCY, LLM_REQUESTS
from time import perf_counter


class EmbeddingError(RuntimeError):
    """Raised when embeddings cannot be generated or validated."""


class _EmbeddingResponse(BaseModel):
    embeddings: list[list[float]]


class OllamaEmbeddings:
    """Generate normalized semantic vectors through Ollama's embed API."""

    def __init__(
        self,
        *,
        base_url: str = settings.ollama_base_url,
        model: str = settings.ollama_embedding_model,
        timeout_seconds: float = settings.ollama_timeout_seconds,
        client: httpx.Client | None = None,
    ) -> None:
        self.model = model
        self._owns_client = client is None
        self._client = client or httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout_seconds
        )

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        clean_texts = [text.strip() for text in texts]
        if not clean_texts:
            return []
        if any(not text for text in clean_texts):
            raise ValueError("Embedding input cannot be empty")

        started = perf_counter()

        def send() -> httpx.Response:
            response = self._client.post(
                "/api/embed",
                json={
                    "model": self.model,
                    "input": clean_texts,
                    "truncate": True,
                },
            )
            response.raise_for_status()
            return response

        try:
            response = retry_sync(
                send,
                attempts=settings.retry_max_attempts,
                base_delay=settings.retry_base_delay_seconds,
                retry_for=(httpx.ConnectError, httpx.TimeoutException),
            )
        except httpx.HTTPStatusError as exc:
            LLM_REQUESTS.labels("embedding", "failure").inc()
            raise EmbeddingError(self._http_error_message(exc.response)) from exc
        except httpx.RequestError as exc:
            LLM_REQUESTS.labels("embedding", "failure").inc()
            raise EmbeddingError("Could not communicate with Ollama embeddings") from exc
        finally:
            LLM_LATENCY.labels("embedding").observe(perf_counter() - started)

        try:
            payload = _EmbeddingResponse.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            LLM_REQUESTS.labels("embedding", "malformed").inc()
            raise EmbeddingError("Ollama returned malformed embeddings") from exc

        if len(payload.embeddings) != len(clean_texts):
            LLM_REQUESTS.labels("embedding", "malformed").inc()
            raise EmbeddingError("Ollama returned an unexpected number of embeddings")
        if any(not vector for vector in payload.embeddings):
            LLM_REQUESTS.labels("embedding", "malformed").inc()
            raise EmbeddingError("Ollama returned an empty embedding vector")
        dimensions = {len(vector) for vector in payload.embeddings}
        if len(dimensions) != 1:
            LLM_REQUESTS.labels("embedding", "malformed").inc()
            raise EmbeddingError("Ollama returned inconsistent embedding dimensions")
        LLM_REQUESTS.labels("embedding", "success").inc()
        return payload.embeddings

    def embed_query(self, query: str) -> list[float]:
        return self.embed_documents([query])[0]

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "OllamaEmbeddings":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @staticmethod
    def _http_error_message(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            payload = None
        detail = payload.get("error") if isinstance(payload, dict) else None
        return f"Ollama embedding request failed: {detail or f'HTTP {response.status_code}'}"
