from sqlalchemy.orm import Session

from app.db.repositories.ticket_repository import TicketRepository
from app.models.ticket import Ticket
from app.schemas.pagination import PageMetadata
from app.schemas.ticket import TicketCreate, TicketPage, TicketRead
from app.schemas.ticket import TicketAnalysisStatus


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

    def set_analysis_state(
        self,
        ticket_id: int,
        *,
        status: TicketAnalysisStatus,
        thread_id: str | None = None,
        error: str | None = None,
    ) -> Ticket | None:
        ticket = self.repository.get(ticket_id)
        if ticket is None:
            return None
        ticket.analysis_status = status.value
        if thread_id is not None:
            ticket.workflow_thread_id = thread_id
        ticket.analysis_error = error
        return self.repository.save(ticket)
