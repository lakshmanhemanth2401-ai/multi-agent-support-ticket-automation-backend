from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.workflow_service import WorkflowExecutionService
from app.graph.workflow import build_support_workflow, default_workflow_dependencies


DatabaseSession = Annotated[Session, Depends(get_db)]


def get_workflow_service(request: Request) -> WorkflowExecutionService:
    service = getattr(request.app.state, "workflow_service", None)
    if service is None:
        dependencies = default_workflow_dependencies()
        service = WorkflowExecutionService(
            dependencies,
            workflow=build_support_workflow(
                dependencies, checkpointer=request.app.state.workflow_checkpointer
            ),
        )
        request.app.state.workflow_service = service
    return service


WorkflowService = Annotated[WorkflowExecutionService, Depends(get_workflow_service)]
