from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.response_agent import ResponseResult
from app.db.database import Base
from app.db.repositories.review_repository import ReviewRepository
from app.models.ticket import Ticket
from app.schemas.review import ReviewAction, ReviewActionRequest, ReviewStatus
from app.services.review_service import InvalidReviewTransitionError, ReviewService


@pytest.fixture
def review_service() -> ReviewService:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    session.add(Ticket(title="Login fails", description="SSO access denied"))
    session.commit()
    service = ReviewService(ReviewRepository(session))
    yield service
    session.close()
    engine.dispose()


def _response(body: str = "Please verify your SSO assignment.") -> ResponseResult:
    return ResponseResult(subject="SSO access next steps", body=body, confidence=0.8, escalation_required=False)


def test_review_stores_generated_response_and_timestamps(review_service: ReviewService) -> None:
    review = review_service.create_pending(ticket_id=1, thread_id="thread-1", response=_response())
    assert review.status is ReviewStatus.PENDING
    assert review.generated_response == "Please verify your SSO assignment."
    assert isinstance(review.created_at, datetime)
    assert isinstance(review.updated_at, datetime)
    assert review.reviewed_at is None


@pytest.mark.parametrize(("action", "expected"), [
    (ReviewAction.APPROVE, ReviewStatus.APPROVED),
    (ReviewAction.REJECT, ReviewStatus.REJECTED),
    (ReviewAction.EDIT, ReviewStatus.EDITED),
    (ReviewAction.REGENERATE, ReviewStatus.REGENERATE_REQUESTED),
])
def test_review_actions_are_persisted(review_service: ReviewService, action: ReviewAction, expected: ReviewStatus) -> None:
    review = review_service.create_pending(ticket_id=1, thread_id=f"thread-{action.value}", response=_response())
    request = ReviewActionRequest(
        action=action, reviewer="reviewer@example.com",
        comments="Please revise." if action in {ReviewAction.REJECT, ReviewAction.REGENERATE} else None,
        edited_subject="Edited subject" if action is ReviewAction.EDIT else None,
        edited_response="Edited customer response" if action is ReviewAction.EDIT else None,
    )
    updated = review_service.apply_action(review.id, request)
    assert updated.status is expected
    assert updated.reviewer == "reviewer@example.com"
    assert updated.reviewed_at is not None
    if action is ReviewAction.EDIT:
        assert updated.edited_response == "Edited customer response"


def test_invalid_review_transition_is_rejected(review_service: ReviewService) -> None:
    review = review_service.create_pending(ticket_id=1, thread_id="thread-invalid", response=_response())
    request = ReviewActionRequest(action=ReviewAction.APPROVE, reviewer="reviewer@example.com")
    review_service.apply_action(review.id, request)
    with pytest.raises(InvalidReviewTransitionError):
        review_service.apply_action(review.id, request)


def test_rejected_review_can_return_to_pending_after_rework(review_service: ReviewService) -> None:
    review = review_service.create_pending(ticket_id=1, thread_id="thread-rework", response=_response())
    review_service.apply_action(review.id, ReviewActionRequest(
        action=ReviewAction.REJECT, reviewer="reviewer@example.com", comments="Clarify step two."
    ))
    reworked = review_service.mark_reworked(review.id, _response("Revised response."))
    assert reworked.status is ReviewStatus.PENDING
    assert reworked.generated_response == "Revised response."
    assert reworked.version == 2
    assert reworked.reviewed_at is None
