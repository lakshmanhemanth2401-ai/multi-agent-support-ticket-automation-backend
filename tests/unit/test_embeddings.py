import json

import httpx
import pytest

from app.rag.embeddings import EmbeddingError, OllamaEmbeddings


def test_ollama_embeddings_sends_batch_and_validates_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.url.path == "/api/embed"
        assert payload == {
            "model": "embeddinggemma",
            "input": ["first", "second"],
            "truncate": True,
        }
        return httpx.Response(
            200,
            json={"model": "embeddinggemma", "embeddings": [[1.0, 0.0], [0.0, 1.0]]},
        )

    http_client = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="http://ollama.test"
    )
    embeddings = OllamaEmbeddings(client=http_client)

    assert embeddings.embed_documents(["first", "second"]) == [
        [1.0, 0.0],
        [0.0, 1.0],
    ]

    http_client.close()


def test_ollama_embeddings_handles_service_error() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(500, json={"error": "model failed to load"})
    )
    http_client = httpx.Client(transport=transport, base_url="http://ollama.test")
    embeddings = OllamaEmbeddings(client=http_client)

    with pytest.raises(EmbeddingError, match="model failed to load"):
        embeddings.embed_query("billing")

    http_client.close()


def test_ollama_embeddings_rejects_wrong_vector_count() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, json={"embeddings": [[1.0, 0.0]]})
    )
    http_client = httpx.Client(transport=transport, base_url="http://ollama.test")
    embeddings = OllamaEmbeddings(client=http_client)

    with pytest.raises(EmbeddingError, match="unexpected number"):
        embeddings.embed_documents(["first", "second"])

    http_client.close()
