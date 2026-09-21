from dataclasses import dataclass
from typing import Any

from langgraph.graph import StateGraph
from langgraph.checkpoint.memory import InMemorySaver

from app.agents.classifier_agent import ClassifierAgent
from app.agents.response_agent import ResponseAgent
from app.agents.solution_agent import SolutionAgent
from app.graph.edges import (
    CLASSIFIER_NODE,
    KNOWLEDGE_NODE,
    RESPONSE_NODE,
    REVIEW_RECORD_NODE,
    HUMAN_REVIEW_NODE,
    SOLUTION_NODE,
    add_workflow_edges,
)
from app.graph.nodes import (
    create_classifier_node,
    create_knowledge_node,
    create_response_node,
    create_solution_node,
    create_review_record_node,
    create_human_review_node,
)
from app.graph.state import WorkflowInput, WorkflowOutput, WorkflowState
from app.services.knowledge_service import KnowledgeService
from app.services.review_service import ReviewService
from app.db.repositories.review_repository import ReviewRepository
from app.db.session import SessionLocal


@dataclass(frozen=True, slots=True)
class WorkflowDependencies:
    classifier: ClassifierAgent
    knowledge_service: KnowledgeService
    solution_agent: SolutionAgent
    response_agent: ResponseAgent
    review_service: ReviewService


def default_workflow_dependencies() -> WorkflowDependencies:
    return WorkflowDependencies(
        classifier=ClassifierAgent(),
        knowledge_service=KnowledgeService(),
        solution_agent=SolutionAgent(),
        response_agent=ResponseAgent(),
        review_service=ReviewService(ReviewRepository(SessionLocal())),
    )


def build_support_workflow(
    dependencies: WorkflowDependencies | None = None,
    *,
    checkpointer: Any | None = None,
) -> Any:
    deps = dependencies or default_workflow_dependencies()
    builder = StateGraph(
        WorkflowState,
        input_schema=WorkflowInput,
        output_schema=WorkflowOutput,
    )
    builder.add_node(CLASSIFIER_NODE, create_classifier_node(deps.classifier))
    builder.add_node(KNOWLEDGE_NODE, create_knowledge_node(deps.knowledge_service))
    builder.add_node(SOLUTION_NODE, create_solution_node(deps.solution_agent))
    builder.add_node(RESPONSE_NODE, create_response_node(deps.response_agent))
    builder.add_node(REVIEW_RECORD_NODE, create_review_record_node(deps.review_service))
    builder.add_node(HUMAN_REVIEW_NODE, create_human_review_node(deps.review_service))
    add_workflow_edges(builder)
    return builder.compile(checkpointer=checkpointer or InMemorySaver())
