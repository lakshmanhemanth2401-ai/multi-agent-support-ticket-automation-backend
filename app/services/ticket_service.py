from sqlalchemy.orm import Session

from app.db.repositories.ticket_repository import TicketRepository
from app.models.ticket import Ticket
from app.schemas.ticket import TicketCreate


class TicketService:
    def __init__(self, db: Session) -> None:
        self.repository = TicketRepository(db)

    def create_ticket(self, ticket_data: TicketCreate) -> Ticket:
        return self.repository.create(ticket_data)

    def list_tickets(self, *, offset: int = 0, limit: int = 100) -> list[Ticket]:
        return self.repository.list(offset=offset, limit=limit)

    def get_ticket(self, ticket_id: int) -> Ticket | None:
        return self.repository.get(ticket_id)
