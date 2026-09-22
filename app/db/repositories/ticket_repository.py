from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.repositories.audit_repository import AuditRepository
from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreate


class TicketRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, ticket_data: TicketCreate) -> Ticket:
        ticket = Ticket(**ticket_data.model_dump(mode="json"))
        self.db.add(ticket)
        self.db.flush()
        AuditRepository(self.db).add(
            ticket_id=ticket.id, action="ticket_created", details={"status": ticket.status}
        )
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def list(self, *, offset: int = 0, limit: int = 100) -> list[Ticket]:
        statement = select(Ticket).order_by(Ticket.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(statement).all())

    def get(self, ticket_id: int) -> Ticket | None:
        return self.db.get(Ticket, ticket_id)
