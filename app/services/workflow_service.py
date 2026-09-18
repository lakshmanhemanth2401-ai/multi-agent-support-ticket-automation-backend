from dataclasses import dataclass
from typing import Any

from app.agents.knowledge_agent import KnowledgeSearchResult
from app.agents.response_agent import ResponseResult
from app.agents.solution_agent import SolutionResult
from app.graph.workflow import WorkflowDependencies, build_support_workflow
from app.llm.structured_output import ClassificationResult


@dataclass(frozen=True, slots=True)
class WorkflowExecutionResult:
    classification: ClassificationResult
    knowledge: KnowledgeSearchResult
    solution: SolutionResult
    response: ResponseResult


class WorkflowExecutionService:
    def __init__(
        self,
        dependencies: WorkflowDependencies | None = None,
        *,
        workflow: Any | None = None,
    ) -> None:
        self.workflow = workflow or build_support_workflow(dependencies)

    async def execute(
        self, *, title: str, description: str
    ) -> WorkflowExecutionResult:
        state = await self.workflow.ainvoke(
            {"title": title, "description": description}
        )
        return WorkflowExecutionResult(
            classification=state["classification"],
            knowledge=state["knowledge"],
            solution=state["solution"],
            response=state["response"],
        )
