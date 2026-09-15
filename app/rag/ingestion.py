from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeDocument
from app.rag.chunking import DocumentChunk, chunk_document, clean_document_text


SUPPORTED_EXTENSIONS = {".md", ".txt"}


@dataclass(frozen=True, slots=True)
class SourceDocument:
    title: str
    content: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


def load_documents(directory: str | Path) -> list[SourceDocument]:
    """Load supported knowledge files and preserve their source metadata."""

    root = Path(directory)
    if not root.exists():
        raise FileNotFoundError(f"Knowledge directory does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Knowledge path is not a directory: {root}")

    documents: list[SourceDocument] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        raw_text = path.read_text(encoding="utf-8-sig")
        front_matter, body = _parse_front_matter(raw_text)
        content = clean_document_text(body)
        if not content:
            continue

        source = path.relative_to(root).as_posix()
        title = str(
            front_matter.get("title") or _title_from_content(content, path.stem)
        )[:250]
        metadata = {
            **front_matter,
            "title": title,
            "source": source,
            "file_type": path.suffix.lower().lstrip("."),
        }
        documents.append(
            SourceDocument(
                title=title,
                content=content,
                source=source,
                metadata=metadata,
            )
        )
    return documents


def create_document_chunks(
    documents: list[SourceDocument],
    *,
    chunk_size: int = 1_000,
    chunk_overlap: int = 150,
) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for document in documents:
        chunks.extend(
            chunk_document(
                document.content,
                source=document.source,
                metadata=document.metadata,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        )
    return chunks


def ingest_directory(
    db: Session,
    directory: str | Path,
    *,
    chunk_size: int = 1_000,
    chunk_overlap: int = 150,
) -> int:
    """Replace existing chunks for loaded sources and persist the current corpus."""

    documents = load_documents(directory)
    chunks = create_document_chunks(
        documents,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    sources = {document.source for document in documents}

    try:
        if sources:
            db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.source.in_(sources)))
        db.add_all(
            KnowledgeDocument(
                title=str(chunk.metadata.get("title", chunk.source)),
                content=chunk.content,
                source=chunk.source,
                document_metadata=chunk.metadata,
            )
            for chunk in chunks
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return len(chunks)


def _parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.startswith("---\n"):
        return {}, normalized

    end = normalized.find("\n---\n", 4)
    if end < 0:
        return {}, normalized

    metadata: dict[str, Any] = {}
    for line in normalized[4:end].splitlines():
        key, separator, value = line.partition(":")
        if not separator or not key.strip():
            continue
        clean_value = value.strip()
        if key.strip() == "tags":
            metadata["tags"] = [tag.strip() for tag in clean_value.split(",") if tag.strip()]
        else:
            metadata[key.strip()] = clean_value
    return metadata, normalized[end + 5 :]


def _title_from_content(content: str, fallback: str) -> str:
    first_line = content.splitlines()[0].lstrip("# ").strip()
    return first_line or fallback.replace("_", " ").replace("-", " ").title()
