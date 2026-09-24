from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.review import Review
from app.schemas.review import ReviewCreate


class ReviewRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, data: ReviewCreate) -> Review:
        review = Review(**data.model_dump(), status="pending")
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review

    def get(self, review_id: int) -> Review | None:
        return self.db.get(Review, review_id)

    def get_by_thread(self, thread_id: str) -> Review | None:
        return self.db.scalar(select(Review).where(Review.workflow_thread_id == thread_id))

    def list(self, *, status: str | None = None, offset: int = 0, limit: int = 100) -> list[Review]:
        statement = select(Review).order_by(Review.created_at.desc()).offset(offset).limit(limit)
        if status is not None:
            statement = statement.where(Review.status == status)
        return list(self.db.scalars(statement).all())

    def save(self, review: Review) -> Review:
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review
