"""
Agent Definition for declarative agent configuration.

This module implements Claude Agent SDK's AgentDefinition pattern for
simplified, declarative agent configuration.

Key features:
- AgentDefinition dataclass for declarative agent specification
- AgentRegistry for managing multiple agent definitions
- Integration with existing Subagent infrastructure
- Conversion utilities between SDK and LangGraph patterns
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentDefinition:
    """
    Declarative agent definition following Claude Agent SDK pattern.

    Provides a simple, declarative way to define agents without complex
    boilerplate. Agents can then be instantiated on-demand.

    Example:
        agents = {
            "code_reviewer": AgentDefinition(
                name="code_reviewer",
                description="Reviews code for issues",
                prompt="You are a code reviewer...",
                tools=["Read", "Grep"],
                model="sonnet"
            )
        }

    Attributes:
        name: Unique identifier for the agent
        description: Human-readable description of what the agent does
        prompt: System prompt/instructions for the agent
        tools: Optional list of tool names the agent can use (None = all)
        model: Optional model override (None = use system default)
        max_tokens: Optional max tokens for responses
        temperature: Optional temperature for sampling
    """

    name: str
    description: str
    prompt: str
    tools: list[str] | None = None
    model: str | None = None
    max_tokens: int | None = None
    temperature: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary representation.

        Returns:
            Dictionary with all agent configuration
        """
        result: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "prompt": self.prompt,
        }

        if self.tools is not None:
            result["tools"] = self.tools

        if self.model is not None:
            result["model"] = self.model

        if self.max_tokens is not None:
            result["max_tokens"] = self.max_tokens

        if self.temperature is not None:
            result["temperature"] = self.temperature

        return result

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> AgentDefinition:
        """
        Create AgentDefinition from dictionary.

        Args:
            config: Dictionary with agent configuration

        Returns:
            AgentDefinition instance
        """
        return cls(
            name=config["name"],
            description=config["description"],
            prompt=config["prompt"],
            tools=config.get("tools"),
            model=config.get("model"),
            max_tokens=config.get("max_tokens"),
            temperature=config.get("temperature"),
        )

    def to_subagent_config(self, task_id: str) -> dict[str, Any]:
        """
        Convert to configuration for Subagent instantiation.

        This bridges the SDK-style AgentDefinition to the existing
        Subagent infrastructure.

        Args:
            task_id: Unique identifier for the task

        Returns:
            Dictionary suitable for Subagent constructor
        """
        config: dict[str, Any] = {
            "task_id": task_id,
            "instructions": self.prompt,
            "system_prompt": self.prompt,
        }

        if self.model is not None:
            config["model"] = self.model

        return config


@dataclass
class AgentRegistry:
    """
    Registry for managing agent definitions.

    Provides a central place to register, retrieve, and manage
    agent definitions.

    Example:
        registry = AgentRegistry()

        registry.register(AgentDefinition(
            name="reviewer",
            description="Reviews code",
            prompt="You are a code reviewer..."
        ))

        agent = registry.get("reviewer")
    """

    _agents: dict[str, AgentDefinition] = field(default_factory=dict)

    def register(self, agent: AgentDefinition) -> None:
        """
        Register an agent definition.

        Args:
            agent: AgentDefinition to register
        """
        self._agents[agent.name] = agent

    def get(self, name: str) -> AgentDefinition | None:
        """
        Get an agent definition by name.

        Args:
            name: Name of the agent to retrieve

        Returns:
            AgentDefinition if found, None otherwise
        """
        return self._agents.get(name)

    def list_agents(self) -> list[str]:
        """
        List all registered agent names.

        Returns:
            List of agent names
        """
        return list(self._agents.keys())

    def unregister(self, name: str) -> None:
        """
        Unregister an agent by name.

        Args:
            name: Name of the agent to unregister
        """
        self._agents.pop(name, None)

    def clear(self) -> None:
        """Clear all registered agents."""
        self._agents.clear()
