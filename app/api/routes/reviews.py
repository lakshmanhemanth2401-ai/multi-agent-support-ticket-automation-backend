from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.dependencies import DatabaseSession, WorkflowService
from app.core.errors import ConflictError, ResourceNotFoundError
from app.db.repositories.review_repository import ReviewRepository
from app.schemas.review import ReviewActionRequest, ReviewRead, ReviewStatus
from app.schemas.workflow import WorkflowRead, WorkflowStatus
from app.services.review_service import (
    InvalidReviewTransitionError,
    ReviewNotFoundError,
    ReviewService,
)
from app.services.workflow_service import WorkflowExecutionResult, WorkflowReviewPause

router = APIRouter(tags=["reviews"])


def _workflow_read(result: WorkflowReviewPause | WorkflowExecutionResult) -> WorkflowRead:
    if isinstance(result, WorkflowReviewPause):
        return WorkflowRead(
            thread_id=result.thread_id,
            status=WorkflowStatus.AWAITING_REVIEW,
            review=result.review,
            response=result.response,
        )
    return WorkflowRead(
        thread_id=result.thread_id,
        status=WorkflowStatus.COMPLETED,
        review=result.review,
        response=result.response,
        classification=result.classification,
        knowledge=result.knowledge,
        solution=result.solution,
    )


@router.get("/reviews", response_model=list[ReviewRead])
def list_reviews(
    db: DatabaseSession,
    review_status: Annotated[ReviewStatus | None, Query(alias="status")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[ReviewRead]:
    return ReviewService(ReviewRepository(db)).list(
        status=review_status, offset=offset, limit=limit
    )


@router.get("/reviews/{review_id}", response_model=ReviewRead)
def get_review(review_id: Annotated[int, Path(gt=0)], db: DatabaseSession) -> ReviewRead:
    try:
        return ReviewService(ReviewRepository(db)).get(review_id)
    except ReviewNotFoundError as exc:
        raise ResourceNotFoundError() from exc


@router.post("/workflows/{thread_id}/review", response_model=WorkflowRead)
async def submit_review(
    thread_id: Annotated[str, Path(min_length=1, max_length=100)],
    request: ReviewActionRequest,
    workflow_service: WorkflowService,
) -> WorkflowRead:
    try:
        result = await workflow_service.submit_review(thread_id=thread_id, request=request)
    except (LookupError, KeyError) as exc:
        raise ResourceNotFoundError() from exc
    except InvalidReviewTransitionError as exc:
        raise ConflictError() from exc
    return _workflow_read(result)
