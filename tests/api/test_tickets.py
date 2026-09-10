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
    assert response.json() == {"detail": "Ticket not found"}


def test_create_ticket_validates_payload(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tickets",
        json={"title": "", "description": "Missing title"},
    )

    assert response.status_code == 422
