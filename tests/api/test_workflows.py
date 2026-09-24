from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.response_agent import ResponseResult
from app.api.dependencies import get_workflow_service
from app.db.database import Base
from app.db.session import get_db
from app.main import app
from app.schemas.review import ReviewRead, ReviewStatus
from app.services.workflow_service import WorkflowExecutionService, WorkflowReviewPause


@pytest.fixture
def workflow_api():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    def override_db():
        with sessions() as session:
            yield session

    workflow = Mock(spec=WorkflowExecutionService)
    workflow.start = AsyncMock()
    workflow.submit_review = AsyncMock()
    workflow.get_status = AsyncMock()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_workflow_service] = lambda: workflow
    with TestClient(app) as client:
        yield client, workflow
    app.dependency_overrides.clear()
    engine.dispose()


def _pause(ticket_id: int = 1) -> WorkflowReviewPause:
    now = datetime.now(timezone.utc)
    review = ReviewRead(
        id=1,
        ticket_id=ticket_id,
        workflow_thread_id="thread-1",
        generated_subject="Support update",
        generated_response="We are investigating.",
        status=ReviewStatus.PENDING,
        reviewer=None,
        reviewer_comments=None,
        edited_subject=None,
        edited_response=None,
        version=1,
        created_at=now,
        updated_at=now,
        reviewed_at=None,
    )
    response = ResponseResult(
        subject="Support update",
        body="We are investigating.",
        confidence=0.8,
        escalation_required=False,
    )
    return WorkflowReviewPause(thread_id="thread-1", review=review, response=response)


def test_start_and_get_workflow(workflow_api) -> None:
    client, workflow = workflow_api
    ticket = client.post(
        "/api/v1/tickets", json={"title": "API down", "description": "HTTP 503"}
    ).json()
    workflow.start.return_value = _pause(ticket["id"])
    workflow.get_status.return_value = _pause(ticket["id"])

    started = client.post(f"/api/v1/workflows/tickets/{ticket['id']}")
    fetched = client.get("/api/v1/workflows/thread-1")

    assert started.status_code == 202
    assert started.json()["status"] == "awaiting_review"
    assert fetched.status_code == 200
    assert fetched.json()["thread_id"] == "thread-1"
    workflow.start.assert_awaited_once()


def test_submit_review_action(workflow_api) -> None:
    client, workflow = workflow_api
    workflow.submit_review.return_value = _pause()

    response = client.post(
        "/api/v1/workflows/thread-1/review",
        json={"action": "reject", "reviewer": "lead@example.com", "comments": "Revise it."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "awaiting_review"
    workflow.submit_review.assert_awaited_once()


def test_ticket_audit_endpoint(workflow_api) -> None:
    client, _ = workflow_api
    ticket = client.post(
        "/api/v1/tickets", json={"title": "VPN issue", "description": "Cannot connect"}
    ).json()

    response = client.get(f"/api/v1/tickets/{ticket['id']}/audit")

    assert response.status_code == 200
    assert response.json()[0]["action"] == "ticket_created"


def test_missing_workflow_returns_structured_404(workflow_api) -> None:
    client, workflow = workflow_api
    workflow.get_status.side_effect = LookupError("missing")

    response = client.get("/api/v1/workflows/missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "resource_not_found"
