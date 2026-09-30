from collections import OrderedDict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeDocument
from app.schemas.knowledge import KnowledgeDocumentRead


class KnowledgeRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_documents(
        self, *, offset: int = 0, limit: int = 100
    ) -> tuple[list[KnowledgeDocumentRead], int]:
        rows = list(
            self.db.scalars(
                select(KnowledgeDocument).order_by(
                    KnowledgeDocument.source, KnowledgeDocument.created_at
                )
            ).all()
        )
        grouped: OrderedDict[str, list[KnowledgeDocument]] = OrderedDict()
        for row in rows:
            grouped.setdefault(row.source or f"document-{row.id}", []).append(row)
        documents: list[KnowledgeDocumentRead] = []
        for source, chunks in grouped.items():
            first = chunks[0]
            metadata = dict(first.document_metadata or {})
            metadata.pop("chunk_index", None)
            metadata.pop("chunk_number", None)
            metadata.pop("chunk_count", None)
            documents.append(
                KnowledgeDocumentRead(
                    id=first.id,
                    title=first.title,
                    source=source,
                    metadata=metadata,
                    created_at=first.created_at,
                    chunk_count=len(chunks),
                )
            )
        return documents[offset : offset + limit], len(documents)
