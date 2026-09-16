from collections.abc import Sequence

import chromadb
import pytest

from app.rag.chunking import DocumentChunk
from app.rag.retriever import KnowledgeRetriever
from app.rag.vector_store import ChromaVectorStore


class DeterministicEmbeddings:
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, query: str) -> list[float]:
        return self._vector(query)

    @staticmethod
    def _vector(text: str) -> list[float]:
        lowered = text.lower()
        if any(word in lowered for word in ("invoice", "billing", "refund", "charge")):
            return [1.0, 0.0, 0.0]
        if any(word in lowered for word in ("sso", "login", "authentication")):
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]


@pytest.fixture
def vector_store() -> ChromaVectorStore:
    client = chromadb.EphemeralClient()
    store = ChromaVectorStore(
        embedding_provider=DeterministicEmbeddings(),
        collection_name="test_support_knowledge",
        client=client,
    )
    yield store
    store.delete_collection()


def _sample_chunks() -> list[DocumentChunk]:
    return [
        DocumentChunk(
            content="Duplicate invoice charges require Billing Operations review.",
            source="billing/duplicate_charges.md",
            metadata={
                "title": "Duplicate Charges",
                "document_id": "FIN-207",
                "tags": ["billing", "refunds"],
                "chunk_index": 0,
            },
        ),
        DocumentChunk(
            content="SSO login failures require the tenant correlation ID.",
            source="identity/sso.md",
            metadata={
                "title": "SSO Troubleshooting",
                "document_id": "IAM-104",
                "tags": ["sso", "access"],
                "chunk_index": 0,
            },
        ),
        DocumentChunk(
            content="API outages across regions require a severity-one incident.",
            source="platform/api_incident.md",
            metadata={
                "title": "API Incident",
                "document_id": "SRE-311",
                "tags": ["api", "incident"],
                "chunk_index": 0,
            },
        ),
    ]


def test_upsert_chunks_creates_and_updates_collection(
    vector_store: ChromaVectorStore,
) -> None:
    chunks = _sample_chunks()

    assert vector_store.upsert_chunks(chunks) == 3
    assert vector_store.count == 3
    assert vector_store.upsert_chunks(chunks) == 3
    assert vector_store.count == 3


def test_semantic_retrieval_returns_ranked_source_metadata(
    vector_store: ChromaVectorStore,
) -> None:
    vector_store.upsert_chunks(_sample_chunks())
    retriever = KnowledgeRetriever(vector_store)

    results = retriever.retrieve("How do I get a duplicate invoice refund?", top_k=2)

    assert len(results) == 2
    assert results[0].source == "billing/duplicate_charges.md"
    assert results[0].metadata["document_id"] == "FIN-207"
    assert results[0].metadata["tags"] == ["billing", "refunds"]
    assert results[0].relevance_score == pytest.approx(1.0)
    assert results[0].distance == pytest.approx(0.0)
    assert 0.0 <= results[1].relevance_score <= 1.0


def test_semantic_retrieval_limits_results_to_collection_size(
    vector_store: ChromaVectorStore,
) -> None:
    vector_store.upsert_chunks(_sample_chunks()[:1])

    results = vector_store.semantic_search("billing question", top_k=10)

    assert len(results) == 1


def test_semantic_retrieval_handles_empty_collection(
    vector_store: ChromaVectorStore,
) -> None:
    assert vector_store.semantic_search("billing question", top_k=3) == []


@pytest.mark.parametrize("query", ["", "   "])
def test_semantic_retrieval_rejects_empty_query(
    vector_store: ChromaVectorStore, query: str
) -> None:
    with pytest.raises(ValueError, match="Query cannot be empty"):
        vector_store.semantic_search(query)


def test_semantic_retrieval_rejects_invalid_top_k(
    vector_store: ChromaVectorStore,
) -> None:
    with pytest.raises(ValueError, match="top_k"):
        vector_store.semantic_search("billing", top_k=0)
