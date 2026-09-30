from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.dependencies import DatabaseSession, SupportUser
from app.schemas.ticket import TicketCreate, TicketPage, TicketRead
from app.services.ticket_service import TicketService
from app.core.errors import ResourceNotFoundError


router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(ticket_data: TicketCreate, db: DatabaseSession, _: SupportUser) -> TicketRead:
    return TicketRead.model_validate(TicketService(db).create_ticket(ticket_data))


@router.get("", response_model=TicketPage)
def list_tickets(
    db: DatabaseSession,
    _: SupportUser,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> TicketPage:
    return TicketService(db).list_tickets(offset=offset, limit=limit)


@router.get("/{ticket_id}", response_model=TicketRead)
def get_ticket(
    ticket_id: Annotated[int, Path(gt=0)], db: DatabaseSession, _: SupportUser
) -> TicketRead:
    ticket = TicketService(db).get_ticket(ticket_id)
    if ticket is None:
        raise ResourceNotFoundError()
    return TicketRead.model_validate(ticket)
