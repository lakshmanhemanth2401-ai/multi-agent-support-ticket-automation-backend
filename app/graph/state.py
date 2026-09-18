from typing import NotRequired, TypedDict

from app.agents.knowledge_agent import KnowledgeSearchResult
from app.agents.response_agent import ResponseResult
from app.agents.solution_agent import SolutionResult
from app.llm.structured_output import ClassificationResult


class WorkflowInput(TypedDict):
    title: str
    description: str


class WorkflowState(WorkflowInput):
    classification: NotRequired[ClassificationResult]
    knowledge: NotRequired[KnowledgeSearchResult]
    solution: NotRequired[SolutionResult]
    response: NotRequired[ResponseResult]


class WorkflowOutput(TypedDict):
    classification: ClassificationResult
    knowledge: KnowledgeSearchResult
    solution: SolutionResult
    response: ResponseResult
