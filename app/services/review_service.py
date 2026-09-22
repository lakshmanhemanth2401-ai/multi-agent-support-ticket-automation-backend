from datetime import datetime, timezone

from app.agents.response_agent import ResponseResult
from app.db.repositories.review_repository import ReviewRepository
from app.db.repositories.audit_repository import AuditRepository
from app.services.audit_service import AuditService
from app.observability.metrics import REVIEWS
from app.schemas.review import (
    ReviewAction,
    ReviewActionRequest,
    ReviewCreate,
    ReviewRead,
    ReviewStatus,
)


class ReviewNotFoundError(LookupError):
    pass


class InvalidReviewTransitionError(ValueError):
    pass


class ReviewService:
    def __init__(self, repository: ReviewRepository, audit_service: AuditService | None = None) -> None:
        self.repository = repository
        self.audit_service = audit_service or AuditService(AuditRepository(repository.db))

    def create_pending(
        self, *, ticket_id: int, thread_id: str, response: ResponseResult
    ) -> ReviewRead:
        existing = self.repository.get_by_thread(thread_id)
        if existing is not None:
            return ReviewRead.model_validate(existing)
        review = self.repository.create(
            ReviewCreate(
                ticket_id=ticket_id,
                workflow_thread_id=thread_id,
                generated_subject=response.subject,
                generated_response=response.body,
            )
        )
        return ReviewRead.model_validate(review)

    def apply_action(self, review_id: int, request: ReviewActionRequest) -> ReviewRead:
        review = self._get(review_id)
        if review.status != ReviewStatus.PENDING.value:
            raise InvalidReviewTransitionError(
                f"Cannot {request.action.value} review in {review.status} status"
            )
        status_by_action = {
            ReviewAction.APPROVE: ReviewStatus.APPROVED,
            ReviewAction.REJECT: ReviewStatus.REJECTED,
            ReviewAction.EDIT: ReviewStatus.EDITED,
            ReviewAction.REGENERATE: ReviewStatus.REGENERATE_REQUESTED,
        }
        review.status = status_by_action[request.action].value
        review.reviewer = request.reviewer
        review.reviewer_comments = request.comments
        review.edited_subject = request.edited_subject
        review.edited_response = request.edited_response
        review.reviewed_at = datetime.now(timezone.utc)
        saved = ReviewRead.model_validate(self.repository.save(review))
        self.audit_service.record_review_action(
            ticket_id=review.ticket_id, action=request.action.value, reviewer=request.reviewer
        )
        REVIEWS.labels(request.action.value).inc()
        return saved

    def mark_reworked(self, review_id: int, response: ResponseResult) -> ReviewRead:
        review = self._get(review_id)
        allowed = {ReviewStatus.REJECTED.value, ReviewStatus.REGENERATE_REQUESTED.value}
        if review.status not in allowed:
            raise InvalidReviewTransitionError(
                f"Cannot rework review in {review.status} status"
            )
        review.generated_subject = response.subject
        review.generated_response = response.body
        review.status = ReviewStatus.PENDING.value
        review.version += 1
        review.reviewed_at = None
        review.edited_subject = None
        review.edited_response = None
        return ReviewRead.model_validate(self.repository.save(review))

    def _get(self, review_id: int):
        review = self.repository.get(review_id)
        if review is None:
            raise ReviewNotFoundError(f"Review {review_id} was not found")
        return review
