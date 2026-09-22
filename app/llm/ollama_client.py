from collections.abc import Mapping, Sequence
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.core.retry import retry_async
from app.observability.metrics import LLM_LATENCY, LLM_REQUESTS
from time import perf_counter


class OllamaError(RuntimeError):
    """Base exception for Ollama client failures."""


class OllamaUnavailableError(OllamaError):
    """Raised when the Ollama service cannot be reached."""


class OllamaResponseError(OllamaError):
    """Raised when Ollama returns an error or malformed response."""


class _OllamaMessage(BaseModel):
    content: str


class _OllamaChatResponse(BaseModel):
    message: _OllamaMessage


class OllamaClient:
    def __init__(
        self,
        *,
        base_url: str = settings.ollama_base_url,
        model: str = settings.ollama_model,
        timeout_seconds: float = settings.ollama_timeout_seconds,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.model = model
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=base_url.rstrip("/"), timeout=timeout_seconds
        )

    async def chat(
        self,
        *,
        messages: Sequence[Mapping[str, str]],
        output_schema: dict[str, Any],
    ) -> str:
        payload = {
            "model": self.model,
            "messages": [dict(message) for message in messages],
            "stream": False,
            "format": output_schema,
            "options": {"temperature": 0},
        }

        started = perf_counter()

        async def send() -> httpx.Response:
            response = await self._client.post("/api/chat", json=payload)
            response.raise_for_status()
            return response

        try:
            response = await retry_async(
                send,
                attempts=settings.retry_max_attempts,
                base_delay=settings.retry_base_delay_seconds,
                retry_for=(httpx.ConnectError, httpx.TimeoutException),
            )
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            LLM_REQUESTS.labels("chat", "failure").inc()
            raise OllamaUnavailableError("Ollama is unavailable") from exc
        except httpx.HTTPStatusError as exc:
            LLM_REQUESTS.labels("chat", "failure").inc()
            detail = self._extract_error(exc.response)
            raise OllamaResponseError(f"Ollama request failed: {detail}") from exc
        except httpx.RequestError as exc:
            LLM_REQUESTS.labels("chat", "failure").inc()
            raise OllamaUnavailableError("Could not communicate with Ollama") from exc
        finally:
            LLM_LATENCY.labels("chat").observe(perf_counter() - started)

        try:
            parsed = _OllamaChatResponse.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            LLM_REQUESTS.labels("chat", "malformed").inc()
            raise OllamaResponseError("Ollama returned a malformed response") from exc

        if not parsed.message.content.strip():
            LLM_REQUESTS.labels("chat", "malformed").inc()
            raise OllamaResponseError("Ollama returned an empty response")
        LLM_REQUESTS.labels("chat", "success").inc()
        return parsed.message.content

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "OllamaClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    @staticmethod
    def _extract_error(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return f"HTTP {response.status_code}"
        error = payload.get("error") if isinstance(payload, dict) else None
        return str(error or f"HTTP {response.status_code}")
