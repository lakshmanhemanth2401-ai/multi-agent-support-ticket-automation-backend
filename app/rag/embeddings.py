from collections.abc import Sequence

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings


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

        try:
            response = self._client.post(
                "/api/embed",
                json={
                    "model": self.model,
                    "input": clean_texts,
                    "truncate": True,
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise EmbeddingError(self._http_error_message(exc.response)) from exc
        except httpx.RequestError as exc:
            raise EmbeddingError("Could not communicate with Ollama embeddings") from exc

        try:
            payload = _EmbeddingResponse.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise EmbeddingError("Ollama returned malformed embeddings") from exc

        if len(payload.embeddings) != len(clean_texts):
            raise EmbeddingError("Ollama returned an unexpected number of embeddings")
        if any(not vector for vector in payload.embeddings):
            raise EmbeddingError("Ollama returned an empty embedding vector")
        dimensions = {len(vector) for vector in payload.embeddings}
        if len(dimensions) != 1:
            raise EmbeddingError("Ollama returned inconsistent embedding dimensions")
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
