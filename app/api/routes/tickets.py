from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import DatabaseSession
from app.schemas.ticket import TicketCreate, TicketRead
from app.services.ticket_service import TicketService


router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(ticket_data: TicketCreate, db: DatabaseSession) -> TicketRead:
    return TicketService(db).create_ticket(ticket_data)


@router.get("", response_model=list[TicketRead])
def list_tickets(
    db: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> list[TicketRead]:
    return TicketService(db).list_tickets(offset=offset, limit=limit)


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket(ticket_id: int, db: DatabaseSession) -> TicketRead:
    ticket = TicketService(db).get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )
    return ticket
