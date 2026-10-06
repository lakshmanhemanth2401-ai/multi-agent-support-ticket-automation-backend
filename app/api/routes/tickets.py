from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Path, Query, Request, status
from uuid import uuid4

from app.api.dependencies import AnalysisRunner, DatabaseSession, SupportUser
from app.schemas.ticket import TicketAnalysisStatus, TicketCreate, TicketPage, TicketRead
from app.services.ticket_service import TicketService
from app.core.errors import ResourceNotFoundError


router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(
    ticket_data: TicketCreate,
    db: DatabaseSession,
    _: SupportUser,
    request: Request,
    background_tasks: BackgroundTasks,
    analysis_runner: AnalysisRunner,
) -> TicketRead:
    service = TicketService(db)
    ticket = service.create_ticket(ticket_data)
    thread_id = str(uuid4())
    updated_ticket = service.set_analysis_state(
        ticket.id,
        status=TicketAnalysisStatus.QUEUED,
        thread_id=thread_id,
    )
    assert updated_ticket is not None
    background_tasks.add_task(
        analysis_runner,
        application=request.app,
        ticket_id=updated_ticket.id,
        thread_id=thread_id,
        title=updated_ticket.title,
        description=updated_ticket.description,
    )
    return TicketRead.model_validate(updated_ticket)


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
