import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import chromadb

from app.core.config import settings
from app.rag.chunking import DocumentChunk
from app.rag.embeddings import OllamaEmbeddings


class EmbeddingProvider(Protocol):
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, query: str) -> list[float]: ...


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    content: str
    source: str
    relevance_score: float
    distance: float
    metadata: dict[str, Any] = field(default_factory=dict)


class ChromaVectorStore:
    """Manage the persistent support-knowledge Chroma collection."""

    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider | None = None,
        persist_directory: str | Path = settings.chroma_persist_directory,
        collection_name: str = settings.chroma_collection_name,
        client: Any | None = None,
    ) -> None:
        self.embedding_provider = embedding_provider or OllamaEmbeddings()
        self.client = client or chromadb.PersistentClient(path=str(persist_directory))
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            configuration={"hnsw": {"space": "cosine"}},
            metadata={"description": "Enterprise support knowledge chunks"},
        )

    @property
    def count(self) -> int:
        return self.collection.count()

    def upsert_chunks(self, chunks: Sequence[DocumentChunk]) -> int:
        if not chunks:
            return 0

        documents = [chunk.content for chunk in chunks]
        embeddings = self.embedding_provider.embed_documents(documents)
        if len(embeddings) != len(chunks):
            raise ValueError("Embedding count must match chunk count")

        ids = [self._chunk_id(chunk) for chunk in chunks]
        metadatas = [self._serialize_metadata(chunk) for chunk in chunks]
        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return len(chunks)

    def semantic_search(self, query: str, *, top_k: int = 5) -> list[RetrievalResult]:
        if not query.strip():
            raise ValueError("Query cannot be empty")
        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")
        if self.count == 0:
            return []

        query_embedding = self.embedding_provider.embed_query(query.strip())
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.count),
            include=["documents", "metadatas", "distances"],
        )
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        matches: list[RetrievalResult] = []
        for content, stored_metadata, raw_distance in zip(
            documents, metadatas, distances, strict=True
        ):
            metadata = self._deserialize_metadata(stored_metadata or {})
            distance = float(raw_distance)
            matches.append(
                RetrievalResult(
                    content=content or "",
                    source=str(metadata.get("source", "unknown")),
                    relevance_score=max(0.0, min(1.0, 1.0 - distance)),
                    distance=distance,
                    metadata=metadata,
                )
            )
        return matches

    def delete_collection(self) -> None:
        self.client.delete_collection(self.collection.name)

    @staticmethod
    def _chunk_id(chunk: DocumentChunk) -> str:
        chunk_index = chunk.metadata.get("chunk_index", 0)
        identity = f"{chunk.source}:{chunk_index}:{chunk.content}".encode("utf-8")
        return hashlib.sha256(identity).hexdigest()

    @staticmethod
    def _serialize_metadata(chunk: DocumentChunk) -> dict[str, str | int | float | bool]:
        metadata = {**chunk.metadata, "source": chunk.source}
        serialized: dict[str, str | int | float | bool] = {}
        json_fields: list[str] = []
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                serialized[key] = value
            elif value is not None:
                serialized[key] = json.dumps(value, sort_keys=True)
                json_fields.append(key)
        if json_fields:
            serialized["_json_fields"] = ",".join(sorted(json_fields))
        return serialized

    @staticmethod
    def _deserialize_metadata(
        metadata: dict[str, str | int | float | bool]
    ) -> dict[str, Any]:
        restored: dict[str, Any] = dict(metadata)
        json_fields = str(restored.pop("_json_fields", "")).split(",")
        for key in filter(None, json_fields):
            value = restored.get(key)
            if isinstance(value, str):
                try:
                    restored[key] = json.loads(value)
                except json.JSONDecodeError:
                    pass
        return restored
