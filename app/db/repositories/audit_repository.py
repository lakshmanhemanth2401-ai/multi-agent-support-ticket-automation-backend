from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, *, ticket_id: int, action: str, details: dict[str, Any] | None = None) -> AuditLog:
        event = AuditLog(ticket_id=ticket_id, action=action, details=details)
        self.db.add(event)
        return event

    def create(self, *, ticket_id: int, action: str, details: dict[str, Any] | None = None) -> AuditLog:
        event = self.add(ticket_id=ticket_id, action=action, details=details)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_for_ticket(self, ticket_id: int) -> list[AuditLog]:
        statement = select(AuditLog).where(AuditLog.ticket_id == ticket_id).order_by(AuditLog.created_at)
        return list(self.db.scalars(statement).all())
