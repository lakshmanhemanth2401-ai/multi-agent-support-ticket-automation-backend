from dataclasses import dataclass
from typing import Any

from langgraph.graph import StateGraph

from app.agents.classifier_agent import ClassifierAgent
from app.agents.response_agent import ResponseAgent
from app.agents.solution_agent import SolutionAgent
from app.graph.edges import (
    CLASSIFIER_NODE,
    KNOWLEDGE_NODE,
    RESPONSE_NODE,
    SOLUTION_NODE,
    add_workflow_edges,
)
from app.graph.nodes import (
    create_classifier_node,
    create_knowledge_node,
    create_response_node,
    create_solution_node,
)
from app.graph.state import WorkflowInput, WorkflowOutput, WorkflowState
from app.services.knowledge_service import KnowledgeService


@dataclass(frozen=True, slots=True)
class WorkflowDependencies:
    classifier: ClassifierAgent
    knowledge_service: KnowledgeService
    solution_agent: SolutionAgent
    response_agent: ResponseAgent


def default_workflow_dependencies() -> WorkflowDependencies:
    return WorkflowDependencies(
        classifier=ClassifierAgent(),
        knowledge_service=KnowledgeService(),
        solution_agent=SolutionAgent(),
        response_agent=ResponseAgent(),
    )


def build_support_workflow(
    dependencies: WorkflowDependencies | None = None,
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
    add_workflow_edges(builder)
    return builder.compile()
