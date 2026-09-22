from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.retry import retry_async
from app.db.database import Base
from app.db.repositories.audit_repository import AuditRepository
from app.models.ticket import Ticket
from app.rag.retriever import KnowledgeRetriever, RetrievalError
from app.services.audit_service import AuditService


def test_audit_service_persists_events_and_redacts_sensitive_data() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    session.add(Ticket(title="VPN", description="Connection fails"))
    session.commit()
    repository = AuditRepository(session)

    AuditService(repository).record(
        ticket_id=1,
        action="classifier_completed",
        details={"category": "network", "api_token": "secret-value", "description": "private ticket text"},
    )

    event = repository.list_for_ticket(1)[0]
    assert event.action == "classifier_completed"
    assert event.details == {"category": "network", "api_token": "[REDACTED]", "description": "[REDACTED]"}
    session.close()
    engine.dispose()


@pytest.mark.asyncio
async def test_controlled_async_retry_stops_after_success() -> None:
    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise TimeoutError("temporary")
        return "ok"

    assert await retry_async(operation, attempts=3, base_delay=0, retry_for=(TimeoutError,)) == "ok"
    assert attempts == 3


def test_retrieval_failure_is_wrapped_after_controlled_retries(monkeypatch) -> None:
    monkeypatch.setattr("app.rag.retriever.settings.retry_base_delay_seconds", 0)
    store = Mock()
    store.semantic_search.side_effect = ConnectionError("chroma unavailable")
    retriever = KnowledgeRetriever(store)

    with pytest.raises(RetrievalError, match="temporarily unavailable"):
        retriever.retrieve("vpn issue")

    assert store.semantic_search.call_count == 3
