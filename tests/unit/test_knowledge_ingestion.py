from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.knowledge import KnowledgeDocument
from app.rag.chunking import chunk_document, clean_document_text
from app.rag.ingestion import create_document_chunks, ingest_directory, load_documents


def test_load_documents_preserves_source_and_front_matter(tmp_path: Path) -> None:
    folder = tmp_path / "identity"
    folder.mkdir()
    (folder / "sso.md").write_text(
        """---
title: SSO Guide
document_id: IAM-1
tags: sso, access
---
# SSO Guide\r\n\r\n  Verify   the tenant.  \r\n\r\n\r\nRetry login.
""",
        encoding="utf-8",
    )
    (folder / "ignored.json").write_text("{}", encoding="utf-8")

    documents = load_documents(tmp_path)

    assert len(documents) == 1
    document = documents[0]
    assert document.title == "SSO Guide"
    assert document.source == "identity/sso.md"
    assert document.metadata["document_id"] == "IAM-1"
    assert document.metadata["tags"] == ["sso", "access"]
    assert document.metadata["file_type"] == "md"
    assert document.content == "# SSO Guide\n\nVerify the tenant.\n\nRetry login."


def test_clean_document_text_normalizes_without_losing_paragraphs() -> None:
    raw = "\ufeffFirst\t paragraph.\r\n\r\n\r\nSecond    paragraph.  "

    assert clean_document_text(raw) == "First paragraph.\n\nSecond paragraph."


def test_chunk_document_respects_size_overlap_and_metadata() -> None:
    text = "\n\n".join(
        [
            "Authentication failures must include a correlation identifier.",
            "Support should verify tenant configuration before escalation.",
            "Secrets and session cookies must always be removed from evidence.",
        ]
    )

    chunks = chunk_document(
        text,
        source="identity/sso.md",
        metadata={"document_id": "IAM-1", "department": "Identity"},
        chunk_size=100,
        chunk_overlap=30,
    )

    assert len(chunks) >= 2
    assert all(len(chunk.content) <= 100 for chunk in chunks)
    assert [chunk.metadata["chunk_index"] for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.metadata["chunk_count"] == len(chunks) for chunk in chunks)
    assert all(chunk.metadata["document_id"] == "IAM-1" for chunk in chunks)
    assert all(chunk.source == "identity/sso.md" for chunk in chunks)


def test_create_document_chunks_preserves_document_metadata(tmp_path: Path) -> None:
    (tmp_path / "guide.txt").write_text(
        "Customer exports expire after seventy-two hours. " * 12,
        encoding="utf-8",
    )

    chunks = create_document_chunks(
        load_documents(tmp_path), chunk_size=150, chunk_overlap=20
    )

    assert len(chunks) > 1
    assert all(chunk.metadata["source"] == "guide.txt" for chunk in chunks)
    titles = {chunk.metadata["title"] for chunk in chunks}
    assert len(titles) == 1
    assert next(iter(titles)).startswith("Customer exports expire")
    assert len(next(iter(titles))) <= 250


def test_ingest_directory_replaces_existing_source_chunks(tmp_path: Path) -> None:
    document_path = tmp_path / "policy.md"
    document_path.write_text(
        "---\ntitle: Retention Policy\ndocument_id: DATA-1\n---\nRetention applies by tenant.",
        encoding="utf-8",
    )
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    with session_factory() as session:
        assert ingest_directory(
            session, tmp_path, chunk_size=100, chunk_overlap=20
        ) == 1
        assert ingest_directory(
            session, tmp_path, chunk_size=100, chunk_overlap=20
        ) == 1
        records = list(session.scalars(select(KnowledgeDocument)).all())

    assert len(records) == 1
    assert records[0].source == "policy.md"
    assert records[0].document_metadata["document_id"] == "DATA-1"
    engine.dispose()
