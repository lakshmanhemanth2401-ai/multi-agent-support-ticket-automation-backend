from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.api.dependencies import DatabaseSession, KnowledgeCatalog, ReviewerUser, SupportUser
from app.core.errors import ResourceNotFoundError
from app.db.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditLogPage, AuditLogRead
from app.schemas.knowledge import (
    KnowledgeDocumentPage,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
)
from app.schemas.pagination import PageMetadata
from app.services.ticket_service import TicketService

router = APIRouter(tags=["knowledge", "audit"])


@router.get("/tickets/{ticket_id}/audit", response_model=AuditLogPage)
def ticket_audit(
    ticket_id: Annotated[int, Path(gt=0)],
    db: DatabaseSession,
    _: ReviewerUser,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> AuditLogPage:
    if TicketService(db).get_ticket(ticket_id) is None:
        raise ResourceNotFoundError()
    events, total = AuditRepository(db).list_for_ticket(ticket_id, offset=offset, limit=limit)
    return AuditLogPage(
        items=[AuditLogRead.model_validate(event) for event in events],
        pagination=PageMetadata(offset=offset, limit=limit, total=total),
    )


@router.get("/knowledge/documents", response_model=KnowledgeDocumentPage)
def list_knowledge_documents(
    service: KnowledgeCatalog,
    _: SupportUser,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
) -> KnowledgeDocumentPage:
    return service.list_documents(offset=offset, limit=limit)


@router.post("/knowledge/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    request: KnowledgeSearchRequest,
    service: KnowledgeCatalog,
    _: SupportUser,
) -> KnowledgeSearchResponse:
    return service.search(query=request.query, top_k=request.top_k)
