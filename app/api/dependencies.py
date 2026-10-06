from collections.abc import Callable, Coroutine
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.workflow_service import WorkflowExecutionService
from app.graph.workflow import build_support_workflow, default_workflow_dependencies
from app.core.errors import AuthenticationError, AuthorizationError
from app.core.security import decode_token
from app.db.repositories.user_repository import UserRepository
from app.models.user import User, UserRole
from app.db.repositories.knowledge_repository import KnowledgeRepository
from app.services.knowledge_catalog_service import KnowledgeCatalogService
from app.rag.retriever import KnowledgeRetriever
from app.services.automatic_analysis_service import run_automatic_ticket_analysis


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

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    db: DatabaseSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError()
    claims = decode_token(credentials.credentials, expected_type="access")
    try:
        user_id = int(str(claims["sub"]))
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthenticationError() from exc
    user = UserRepository(db).get(user_id)
    if user is None or not user.is_active:
        raise AuthenticationError()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    allowed = {role.value for role in roles}

    def authorize(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise AuthorizationError()
        return user

    return authorize


SupportUser = Annotated[
    User,
    Depends(require_roles(UserRole.SUPPORT_AGENT, UserRole.REVIEWER, UserRole.ADMINISTRATOR)),
]
ReviewerUser = Annotated[User, Depends(require_roles(UserRole.REVIEWER, UserRole.ADMINISTRATOR))]
AdministratorUser = Annotated[User, Depends(require_roles(UserRole.ADMINISTRATOR))]


def get_knowledge_catalog(db: DatabaseSession, request: Request) -> KnowledgeCatalogService:
    retriever = getattr(request.app.state, "knowledge_retriever", None)
    if retriever is None:
        retriever = KnowledgeRetriever()
        request.app.state.knowledge_retriever = retriever
    return KnowledgeCatalogService(KnowledgeRepository(db), retriever)


KnowledgeCatalog = Annotated[KnowledgeCatalogService, Depends(get_knowledge_catalog)]


AutomaticAnalysisRunner = Callable[..., Coroutine[Any, Any, None]]


def get_automatic_analysis_runner() -> AutomaticAnalysisRunner:
    return run_automatic_ticket_analysis


AnalysisRunner = Annotated[AutomaticAnalysisRunner, Depends(get_automatic_analysis_runner)]
