from typing import Annotated

from fastapi import APIRouter, Path, status

from app.api.dependencies import DatabaseSession, SupportUser, WorkflowService
from app.core.errors import ResourceNotFoundError
from app.core.errors import AnalysisInProgressError
from app.schemas.ticket import TicketAnalysisStatus
from app.schemas.workflow import WorkflowRead
from app.services.ticket_service import TicketService
from app.services.workflow_service import WorkflowExecutionResult, WorkflowReviewPause
from app.api.routes.reviews import _workflow_read

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post(
    "/tickets/{ticket_id}", response_model=WorkflowRead, status_code=status.HTTP_202_ACCEPTED
)
async def start_workflow(
    ticket_id: Annotated[int, Path(gt=0)],
    db: DatabaseSession,
    workflow_service: WorkflowService,
    _: SupportUser,
) -> WorkflowRead:
    ticket = TicketService(db).get_ticket(ticket_id)
    if ticket is None:
        raise ResourceNotFoundError()
    if ticket.workflow_thread_id:
        try:
            existing = await workflow_service.get_status(thread_id=ticket.workflow_thread_id)
        except LookupError:
            if ticket.analysis_status in {
                TicketAnalysisStatus.QUEUED.value,
                TicketAnalysisStatus.RUNNING.value,
            }:
                raise AnalysisInProgressError() from None
        else:
            return _workflow_read(existing)
    restart_thread_id = (
        None
        if ticket.analysis_status == TicketAnalysisStatus.FAILED.value
        else ticket.workflow_thread_id
    )
    result = await workflow_service.start(
        ticket_id=ticket.id,
        title=ticket.title,
        description=ticket.description,
        thread_id=restart_thread_id,
    )
    TicketService(db).set_analysis_state(
        ticket.id,
        status=TicketAnalysisStatus.AWAITING_REVIEW,
        thread_id=result.thread_id,
    )
    return _workflow_read(result)


@router.get("/tickets/{ticket_id}", response_model=WorkflowRead)
async def get_ticket_workflow(
    ticket_id: Annotated[int, Path(gt=0)],
    db: DatabaseSession,
    workflow_service: WorkflowService,
    _: SupportUser,
) -> WorkflowRead:
    ticket = TicketService(db).get_ticket(ticket_id)
    if ticket is None or ticket.workflow_thread_id is None:
        raise ResourceNotFoundError()
    try:
        result = await workflow_service.get_status(thread_id=ticket.workflow_thread_id)
    except LookupError as exc:
        if ticket.analysis_status in {
            TicketAnalysisStatus.QUEUED.value,
            TicketAnalysisStatus.RUNNING.value,
        }:
            raise AnalysisInProgressError() from exc
        raise ResourceNotFoundError() from exc
    return _workflow_read(result)


@router.get("/{thread_id}", response_model=WorkflowRead)
async def get_workflow(
    thread_id: Annotated[str, Path(min_length=1, max_length=100)],
    workflow_service: WorkflowService,
    _: SupportUser,
) -> WorkflowRead:
    try:
        result: WorkflowReviewPause | WorkflowExecutionResult = await workflow_service.get_status(
            thread_id=thread_id
        )
    except LookupError as exc:
        raise ResourceNotFoundError() from exc
    return _workflow_read(result)
