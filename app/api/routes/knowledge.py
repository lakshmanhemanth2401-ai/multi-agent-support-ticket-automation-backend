from typing import Annotated

from fastapi import APIRouter, Path

from app.api.dependencies import DatabaseSession
from app.core.errors import ResourceNotFoundError
from app.db.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditLogRead
from app.services.ticket_service import TicketService

router = APIRouter(prefix="/tickets", tags=["audit"])


@router.get("/{ticket_id}/audit", response_model=list[AuditLogRead])
def ticket_audit(
    ticket_id: Annotated[int, Path(gt=0)], db: DatabaseSession
) -> list[AuditLogRead]:
    if TicketService(db).get_ticket(ticket_id) is None:
        raise ResourceNotFoundError()
    return [
        AuditLogRead.model_validate(event)
        for event in AuditRepository(db).list_for_ticket(ticket_id)
    ]
