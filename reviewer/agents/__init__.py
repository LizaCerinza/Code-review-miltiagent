from .base import Agent, AgentError
from .design import DesignAgent
from .functional import FunctionalAgent
from .security import SecurityAgent


def default_agents() -> list[Agent]:
    return [FunctionalAgent(), SecurityAgent(), DesignAgent()]


__all__ = ["Agent", "AgentError", "DesignAgent", "FunctionalAgent", "SecurityAgent",
           "default_agents"]
