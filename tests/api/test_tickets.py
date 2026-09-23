import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture
def client() -> TestClient:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_create_ticket(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tickets",
        json={
            "title": "Cannot sign in",
            "description": "The login page rejects valid credentials.",
            "priority": "high",
            "category": "authentication",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] == 1
    assert payload["status"] == "open"
    assert payload["priority"] == "high"


def test_list_and_get_tickets(client: TestClient) -> None:
    created = client.post(
        "/api/v1/tickets",
        json={"title": "Billing issue", "description": "Duplicate charge."},
    ).json()

    list_response = client.get("/api/v1/tickets")
    assert list_response.status_code == 200
    assert [ticket["id"] for ticket in list_response.json()] == [created["id"]]

    get_response = client.get(f"/api/v1/tickets/{created['id']}")
    assert get_response.status_code == 200
    assert get_response.json() == created


def test_get_missing_ticket_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/tickets/999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "resource_not_found"
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


def test_create_ticket_validates_payload(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tickets",
        json={"title": "", "description": "Missing title"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "   ", "description": "Valid description"},
        {"title": "Valid", "description": "   "},
        {"title": "Valid", "description": "Valid", "unexpected": "field"},
        {"title": "Valid", "description": "Valid", "category": "invalid/category"},
    ],
)
def test_create_ticket_rejects_unsafe_or_unknown_input(client: TestClient, payload: dict) -> None:
    response = client.post("/api/v1/tickets", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_invalid_request_id_is_replaced(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Request-ID": "invalid request id\n"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "invalid request id\n"


def test_metrics_endpoint_and_request_correlation(client: TestClient) -> None:
    response = client.get("/metrics", headers={"X-Request-ID": "test-request-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request-123"
    assert "support_tickets_processed_total" in response.text
    assert "support_agent_executions_total" in response.text
    assert "support_llm_request_duration_seconds" in response.text
    assert "support_retrieval_duration_seconds" in response.text
    assert "support_workflow_duration_seconds" in response.text
    assert "support_reviews_total" in response.text
