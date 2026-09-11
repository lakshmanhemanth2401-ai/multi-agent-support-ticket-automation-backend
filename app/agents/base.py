from abc import ABC, abstractmethod
from typing import Generic, TypeVar


AgentInput = TypeVar("AgentInput")
AgentOutput = TypeVar("AgentOutput")


class BaseAgent(ABC, Generic[AgentInput, AgentOutput]):
    @abstractmethod
    async def run(self, agent_input: AgentInput) -> AgentOutput:
        """Run the agent for one input."""
