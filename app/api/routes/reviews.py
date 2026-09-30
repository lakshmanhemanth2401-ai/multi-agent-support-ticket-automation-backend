from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.dependencies import DatabaseSession, ReviewerUser, WorkflowService
from app.core.errors import ConflictError, ResourceNotFoundError
from app.db.repositories.review_repository import ReviewRepository
from app.schemas.review import ReviewActionRequest, ReviewPage, ReviewRead, ReviewStatus
from app.schemas.workflow import (
    ClassificationRead,
    GeneratedResponseRead,
    KnowledgeContextRead,
    RetrievedKnowledgeRead,
    SolutionRead,
    SupportingSourceRead,
    WorkflowRead,
    WorkflowStatus,
)
from app.services.review_service import (
    InvalidReviewTransitionError,
    ReviewNotFoundError,
    ReviewService,
)
from app.services.workflow_service import WorkflowExecutionResult, WorkflowReviewPause

router = APIRouter(tags=["reviews"])


def _workflow_read(result: WorkflowReviewPause | WorkflowExecutionResult) -> WorkflowRead:
    classification = result.classification
    knowledge = result.knowledge
    solution = result.solution
    if classification is None or knowledge is None or solution is None:
        raise RuntimeError("Workflow state is incomplete")
    sources = [
        SupportingSourceRead(
            source=item.source,
            title=item.title,
            relevance_score=item.relevance_score,
        )
        for item in solution.supporting_sources
    ]
    return WorkflowRead(
        thread_id=result.thread_id,
        status=(
            WorkflowStatus.AWAITING_REVIEW
            if isinstance(result, WorkflowReviewPause)
            else WorkflowStatus.COMPLETED
        ),
        review=result.review,
        classification=ClassificationRead(
            category=classification.category,
            priority=classification.priority,
            confidence=classification.confidence,
        ),
        knowledge=KnowledgeContextRead(
            chunks=[
                RetrievedKnowledgeRead(
                    content=item.content,
                    source=item.source,
                    metadata=item.metadata,
                    relevance_score=item.relevance_score,
                )
                for item in knowledge.results
            ],
            confidence=knowledge.confidence,
            sufficient=knowledge.sufficient,
        ),
        solution=SolutionRead(
            summary=solution.summary,
            troubleshooting_steps=solution.troubleshooting_steps,
            supporting_sources=sources,
            confidence=solution.confidence,
            escalation_required=solution.escalation_required,
            escalation_reason=solution.escalation_reason,
        ),
        generated_response=GeneratedResponseRead(
            subject=result.response.subject,
            body=result.response.body,
            confidence=result.response.confidence,
            escalation_required=result.response.escalation_required,
            supporting_sources=sources,
        ),
        confidence=min(
            classification.confidence,
            knowledge.confidence,
            solution.confidence,
            result.response.confidence,
        ),
        escalation_required=solution.escalation_required or result.response.escalation_required,
    )


@router.get("/reviews", response_model=ReviewPage)
def list_reviews(
    db: DatabaseSession,
    _: ReviewerUser,
    review_status: Annotated[ReviewStatus | None, Query(alias="status")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> ReviewPage:
    return ReviewService(ReviewRepository(db)).list(
        status=review_status, offset=offset, limit=limit
    )


@router.get("/reviews/{review_id}", response_model=ReviewRead)
def get_review(
    review_id: Annotated[int, Path(gt=0)], db: DatabaseSession, _: ReviewerUser
) -> ReviewRead:
    try:
        return ReviewService(ReviewRepository(db)).get(review_id)
    except ReviewNotFoundError as exc:
        raise ResourceNotFoundError() from exc


@router.post("/workflows/{thread_id}/review", response_model=WorkflowRead)
async def submit_review(
    thread_id: Annotated[str, Path(min_length=1, max_length=100)],
    request: ReviewActionRequest,
    workflow_service: WorkflowService,
    _: ReviewerUser,
) -> WorkflowRead:
    request = request.model_copy(update={"reviewer": _.email})
    try:
        result = await workflow_service.submit_review(thread_id=thread_id, request=request)
    except (LookupError, KeyError) as exc:
        raise ResourceNotFoundError() from exc
    except InvalidReviewTransitionError as exc:
        raise ConflictError() from exc
    return _workflow_read(result)
