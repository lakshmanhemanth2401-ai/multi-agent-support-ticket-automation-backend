from sqlalchemy.orm import Session

from app.db.repositories.ticket_repository import TicketRepository
from app.models.ticket import Ticket
from app.schemas.pagination import PageMetadata
from app.schemas.ticket import TicketCreate, TicketPage, TicketRead


class TicketService:
    def __init__(self, db: Session) -> None:
        self.repository = TicketRepository(db)

    def create_ticket(self, ticket_data: TicketCreate) -> Ticket:
        return self.repository.create(ticket_data)

    def list_tickets(self, *, offset: int = 0, limit: int = 100) -> TicketPage:
        items = self.repository.list(offset=offset, limit=limit)
        return TicketPage(
            items=[TicketRead.model_validate(item) for item in items],
            pagination=PageMetadata(offset=offset, limit=limit, total=self.repository.count()),
        )

    def get_ticket(self, ticket_id: int) -> Ticket | None:
        return self.repository.get(ticket_id)
