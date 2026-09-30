from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(
        self, *, ticket_id: int, action: str, details: dict[str, Any] | None = None
    ) -> AuditLog:
        event = AuditLog(ticket_id=ticket_id, action=action, details=details)
        self.db.add(event)
        return event

    def create(
        self, *, ticket_id: int, action: str, details: dict[str, Any] | None = None
    ) -> AuditLog:
        event = self.add(ticket_id=ticket_id, action=action, details=details)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_for_ticket(
        self, ticket_id: int, *, offset: int = 0, limit: int = 100
    ) -> tuple[list[AuditLog], int]:
        condition = AuditLog.ticket_id == ticket_id
        total = self.db.scalar(select(func.count()).select_from(AuditLog).where(condition)) or 0
        statement = (
            select(AuditLog)
            .where(condition)
            .order_by(AuditLog.created_at)
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.scalars(statement).all()), total
