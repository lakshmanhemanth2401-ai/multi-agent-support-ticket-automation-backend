import logging
from typing import Any

from app.graph.workflow import build_support_workflow, default_workflow_dependencies
from app.schemas.ticket import TicketAnalysisStatus
from app.services.ticket_service import TicketService
from app.services.workflow_service import WorkflowExecutionService
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


async def run_automatic_ticket_analysis(
    *,
    application: Any,
    ticket_id: int,
    thread_id: str,
    title: str,
    description: str,
) -> None:
    """Run one ticket workflow after its create response has been sent."""

    with SessionLocal() as state_db:
        TicketService(state_db).set_analysis_state(
            ticket_id,
            status=TicketAnalysisStatus.RUNNING,
            thread_id=thread_id,
        )

    dependencies = default_workflow_dependencies()
    try:
        workflow = build_support_workflow(
            dependencies,
            checkpointer=application.state.workflow_checkpointer,
        )
        service = WorkflowExecutionService(dependencies, workflow=workflow)
        await service.start(
            ticket_id=ticket_id,
            title=title,
            description=description,
            thread_id=thread_id,
        )
        with SessionLocal() as state_db:
            TicketService(state_db).set_analysis_state(
                ticket_id,
                status=TicketAnalysisStatus.AWAITING_REVIEW,
                thread_id=thread_id,
            )
    except Exception:
        logger.exception(
            "automatic_ticket_analysis_failed",
            extra={"event": "workflow_failure", "ticket_id": ticket_id},
        )
        with SessionLocal() as state_db:
            TicketService(state_db).set_analysis_state(
                ticket_id,
                status=TicketAnalysisStatus.FAILED,
                thread_id=thread_id,
                error="analysis_failed",
            )
    finally:
        await dependencies.classifier.client.close()
        await dependencies.solution_agent.client.close()
        await dependencies.response_agent.client.close()
        embedding_provider = (
            dependencies.knowledge_service.agent.retriever.vector_store.embedding_provider
        )
        close_embeddings = getattr(embedding_provider, "close", None)
        if close_embeddings is not None:
            close_embeddings()
        dependencies.review_service.repository.db.close()
