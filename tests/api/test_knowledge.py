from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_user, get_knowledge_catalog
from app.core.errors import DependencyUnavailableError
from app.main import app
from app.models.user import User, UserRole
from app.schemas.knowledge import (
    KnowledgeDocumentPage,
    KnowledgeDocumentRead,
    KnowledgeSearchResponse,
    KnowledgeSearchResultRead,
)
from app.schemas.pagination import PageMetadata
from app.services.knowledge_catalog_service import KnowledgeCatalogService


@pytest.fixture
def knowledge_client():
    service = Mock(spec=KnowledgeCatalogService)
    app.dependency_overrides[get_knowledge_catalog] = lambda: service
    app.dependency_overrides[get_current_user] = lambda: User(
        id=1,
        email="agent@example.com",
        password_hash="unused",
        role=UserRole.SUPPORT_AGENT.value,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    with TestClient(app) as client:
        yield client, service
    app.dependency_overrides.clear()


def test_list_indexed_knowledge_documents(knowledge_client) -> None:
    client, service = knowledge_client
    service.list_documents.return_value = KnowledgeDocumentPage(
        items=[
            KnowledgeDocumentRead(
                id=10,
                title="SSO Troubleshooting",
                source="identity/sso.md",
                metadata={"department": "identity"},
                created_at=datetime.now(timezone.utc),
                chunk_count=3,
            )
        ],
        pagination=PageMetadata(offset=0, limit=20, total=1),
    )

    response = client.get("/api/v1/knowledge/documents?limit=20")

    assert response.status_code == 200
    assert response.json()["items"][0]["chunk_count"] == 3
    assert response.json()["pagination"]["total"] == 1


def test_semantic_knowledge_search_and_empty_results(knowledge_client) -> None:
    client, service = knowledge_client
    service.search.return_value = KnowledgeSearchResponse(
        items=[
            KnowledgeSearchResultRead(
                content="Check the SSO assignment.",
                source="identity/sso.md",
                metadata={"chunk_number": 1},
                relevance_score=0.91,
            )
        ],
        count=1,
    )
    response = client.post(
        "/api/v1/knowledge/search", json={"query": "SSO login failure", "top_k": 3}
    )
    assert response.status_code == 200
    assert response.json()["items"][0]["relevance_score"] == 0.91

    service.search.return_value = KnowledgeSearchResponse(items=[], count=0)
    empty = client.post("/api/v1/knowledge/search", json={"query": "unknown issue", "top_k": 3})
    assert empty.status_code == 200
    assert empty.json() == {"items": [], "count": 0}


@pytest.mark.parametrize(
    "payload",
    [{"query": "", "top_k": 5}, {"query": "valid", "top_k": 0}, {"query": "valid", "top_k": 21}],
)
def test_knowledge_search_validation(knowledge_client, payload: dict) -> None:
    client, _ = knowledge_client
    response = client.post("/api/v1/knowledge/search", json=payload)
    assert response.status_code == 422


def test_knowledge_search_dependency_failure_is_structured(knowledge_client) -> None:
    client, service = knowledge_client
    service.search.side_effect = DependencyUnavailableError()
    response = client.post("/api/v1/knowledge/search", json={"query": "SSO login", "top_k": 5})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "dependency_unavailable"
