import re
from dataclasses import dataclass, field
from typing import Any


_WHITESPACE = re.compile(r"[ \t]+")
_EXCESS_BLANK_LINES = re.compile(r"\n{3,}")


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    content: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


def clean_document_text(text: str) -> str:
    """Normalize document text while preserving meaningful paragraph boundaries."""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").replace("\ufeff", "")
    lines = [_WHITESPACE.sub(" ", line).strip() for line in normalized.split("\n")]
    return _EXCESS_BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()


def chunk_document(
    text: str,
    *,
    source: str,
    metadata: dict[str, Any] | None = None,
    chunk_size: int = 1_000,
    chunk_overlap: int = 150,
) -> list[DocumentChunk]:
    """Split cleaned text into paragraph-aware, overlapping chunks."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be non-negative and smaller than chunk_size")

    cleaned = clean_document_text(text)
    if not cleaned:
        return []

    pieces = _split_oversized_paragraphs(cleaned, chunk_size)
    contents: list[str] = []
    current = ""

    for piece in pieces:
        candidate = f"{current}\n\n{piece}" if current else piece
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            contents.append(current)
            available_overlap = max(0, chunk_size - len(piece) - 2)
            overlap = _select_overlap(current, min(chunk_overlap, available_overlap))
            candidate = f"{overlap}\n\n{piece}" if overlap else piece
        current = candidate

    if current:
        contents.append(current)

    base_metadata = dict(metadata or {})
    chunk_count = len(contents)
    return [
        DocumentChunk(
            content=content,
            source=source,
            metadata={
                **base_metadata,
                "source": source,
                "chunk_index": index,
                "chunk_number": index + 1,
                "chunk_count": chunk_count,
            },
        )
        for index, content in enumerate(contents)
    ]


def _split_oversized_paragraphs(text: str, chunk_size: int) -> list[str]:
    pieces: list[str] = []
    for paragraph in text.split("\n\n"):
        if len(paragraph) <= chunk_size:
            pieces.append(paragraph)
            continue

        remaining = paragraph
        while len(remaining) > chunk_size:
            split_at = remaining.rfind(" ", 0, chunk_size + 1)
            if split_at <= 0:
                split_at = chunk_size
            pieces.append(remaining[:split_at].strip())
            remaining = remaining[split_at:].strip()
        if remaining:
            pieces.append(remaining)
    return pieces


def _select_overlap(content: str, overlap_size: int) -> str:
    if overlap_size == 0:
        return ""
    tail = content[-overlap_size:]
    first_space = tail.find(" ")
    return tail[first_space + 1 :].strip() if first_space >= 0 else tail.strip()
