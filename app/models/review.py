from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), index=True
    )
    workflow_thread_id: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)
    generated_subject: Mapped[str | None] = mapped_column(String(200))
    generated_response: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    reviewer: Mapped[str | None] = mapped_column(String(150))
    reviewer_comments: Mapped[str | None] = mapped_column(Text)
    edited_subject: Mapped[str | None] = mapped_column(String(200))
    edited_response: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    ticket: Mapped["Ticket"] = relationship(back_populates="reviews")
