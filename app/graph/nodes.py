from collections.abc import Awaitable, Callable
from typing import Any

from app.agents.classifier_agent import ClassifierAgent
from app.agents.response_agent import ResponseAgent
from app.agents.solution_agent import SolutionAgent
from app.graph.state import WorkflowState
from app.services.knowledge_service import KnowledgeService


WorkflowNode = Callable[[WorkflowState], Awaitable[dict[str, Any]]]


def create_classifier_node(agent: ClassifierAgent) -> WorkflowNode:
    async def classify(state: WorkflowState) -> dict[str, Any]:
        result = await agent.classify(
            title=state["title"], description=state["description"]
        )
        return {"classification": result}

    return classify


def create_knowledge_node(service: KnowledgeService) -> WorkflowNode:
    async def search(state: WorkflowState) -> dict[str, Any]:
        result = await service.search_for_ticket(
            title=state["title"],
            description=state["description"],
            classification=state["classification"],
        )
        return {"knowledge": result}

    return search


def create_solution_node(agent: SolutionAgent) -> WorkflowNode:
    async def solve(state: WorkflowState) -> dict[str, Any]:
        result = await agent.generate(
            title=state["title"],
            description=state["description"],
            classification=state["classification"],
            knowledge=state["knowledge"],
        )
        return {"solution": result}

    return solve


def create_response_node(agent: ResponseAgent) -> WorkflowNode:
    async def respond(state: WorkflowState) -> dict[str, Any]:
        result = await agent.generate(
            title=state["title"],
            description=state["description"],
            classification=state["classification"],
            knowledge=state["knowledge"],
            solution=state["solution"],
        )
        return {"response": result}

    return respond
