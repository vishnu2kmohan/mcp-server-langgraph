"""CapabilityProvider protocol and supporting types.

Provides the core abstraction for hierarchical capability resolution.
Agents use CapabilityProvider to obtain tools, skills, and memory
based on the current scope (enterprise→task hierarchy).

This follows the composition-over-inheritance pattern from ADR-0092,
enabling any agent to become tool-aware and skill-aware by injecting
a CapabilityProvider.

Usage:
    from mcp_server_langgraph.capabilities.provider import (
        CapabilityProvider,
        ToolSpec,
        SkillSpec,
        MemoryContext,
        ResolvedCapabilities,
        NullCapabilityProvider,
    )

    class MyCapabilityProvider:
        async def get_tools(self, scope, ...) -> list[ToolSpec]:
            ...

    agent = WorkerAgent(llm_factory, capability_provider=MyCapabilityProvider())

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from mcp_server_langgraph.core.scopes import CapabilityScope


@dataclass
class ToolSpec:
    """Specification for a tool that can be bound to an agent.

    Tools are executable functions that agents can invoke during
    task execution. ToolSpec provides the metadata needed for
    LLM function calling.

    Attributes:
        name: Unique identifier for the tool
        description: Human-readable description (used in LLM prompts)
        schema: Optional JSON Schema for tool parameters
        callable: Optional reference to the actual tool function
        scope: Optional scope where this tool is defined
    """

    name: str
    description: str
    schema: dict[str, Any] | None = None
    callable: Any | None = None
    scope: CapabilityScope | None = None


@dataclass
class SkillSpec:
    """Specification for a skill that can be invoked by an agent.

    Skills are higher-level capabilities that may compose multiple
    tools or execute multi-step workflows. They represent reusable
    patterns of agent behavior.

    Attributes:
        name: Unique identifier for the skill
        description: Human-readable description (used in prompts)
        category: Optional category for grouping (e.g., "text", "code")
        tags: Optional tags for discovery and filtering
        scope: Optional scope where this skill is defined
    """

    name: str
    description: str
    category: str | None = None
    tags: list[str] | None = None
    scope: CapabilityScope | None = None


@dataclass
class MemoryContext:
    """Memory context for agent execution.

    Provides hierarchical memory organized by tier:
    - working_memory: Ephemeral task-level memory
    - session_memory: Session-scoped memory (Redis-backed)
    - durable_memory: Persistent memory (PostgreSQL-backed)

    Attributes:
        working_memory: Dict of current task context
        session_memory: List of recent session items
        durable_memory: List of persistent items
        relevant_memories: Semantically retrieved memories
    """

    working_memory: dict[str, Any] = field(default_factory=dict)
    session_memory: list[Any] = field(default_factory=list)
    durable_memory: list[Any] = field(default_factory=list)
    relevant_memories: list[Any] = field(default_factory=list)


@dataclass
class ResolvedCapabilities:
    """Container for resolved capabilities from a CapabilityProvider.

    Represents the complete set of capabilities available to an agent
    for a specific task, after hierarchical scope resolution.

    Attributes:
        tools: List of tools available for this task
        skills: List of skills available for this task
        memory: Memory context for this task
        scope: The scope at which capabilities were resolved
    """

    tools: list[ToolSpec]
    skills: list[SkillSpec]
    memory: MemoryContext | None
    scope: CapabilityScope | None = None

    def __post_init__(self) -> None:
        """Set default scope to TASK if not provided."""
        if self.scope is None:
            from mcp_server_langgraph.core.scopes import CapabilityScope

            self.scope = CapabilityScope.TASK


@runtime_checkable
class CapabilityProvider(Protocol):
    """Protocol for hierarchical capability resolution.

    CapabilityProvider is the core abstraction enabling composition-based
    tool and skill awareness. Any class implementing this protocol can
    be injected into agents to provide capabilities.

    The protocol defines three async methods:
    - get_tools: Resolve tools for a scope
    - get_skills: Resolve skills for a scope
    - get_memory: Retrieve memory context for a scope

    Implementation Notes:
    - Methods should respect the scope hierarchy (task→enterprise)
    - Lower scopes override higher scopes for same-named capabilities
    - Results may be cached for performance

    Example:
        class HierarchicalCapabilityProvider:
            async def get_tools(self, scope, names=None) -> list[ToolSpec]:
                # Resolve from STUDIO.md hierarchy
                ...

            async def get_skills(self, scope, names=None) -> list[SkillSpec]:
                # Resolve from skill registry
                ...

            async def get_memory(self, scope, query=None) -> MemoryContext:
                # Retrieve relevant memories
                ...
    """

    async def get_tools(
        self,
        scope: CapabilityScope,
        names: list[str] | None = None,
    ) -> list[ToolSpec]:
        """Get tools available at the specified scope.

        Args:
            scope: CapabilityScope for resolution (e.g., TASK, PROJECT)
            names: Optional filter for specific tool names

        Returns:
            List of ToolSpec objects available at this scope
        """
        ...

    async def get_skills(
        self,
        scope: CapabilityScope,
        names: list[str] | None = None,
    ) -> list[SkillSpec]:
        """Get skills available at the specified scope.

        Args:
            scope: CapabilityScope for resolution
            names: Optional filter for specific skill names

        Returns:
            List of SkillSpec objects available at this scope
        """
        ...

    async def get_memory(
        self,
        scope: CapabilityScope,
        query: str | None = None,
    ) -> MemoryContext:
        """Get memory context for the specified scope.

        Args:
            scope: CapabilityScope for memory retrieval
            query: Optional semantic query for relevant memories

        Returns:
            MemoryContext with working/session/durable memories
        """
        ...


class NullCapabilityProvider:
    """No-op CapabilityProvider for backward compatibility.

    Returns empty results for all methods. Use this when agents
    should operate without capability injection (legacy behavior).
    """

    async def get_tools(
        self,
        scope: CapabilityScope,
        names: list[str] | None = None,
    ) -> list[ToolSpec]:
        """Return empty tool list."""
        return []

    async def get_skills(
        self,
        scope: CapabilityScope,
        names: list[str] | None = None,
    ) -> list[SkillSpec]:
        """Return empty skill list."""
        return []

    async def get_memory(
        self,
        scope: CapabilityScope,
        query: str | None = None,
    ) -> MemoryContext:
        """Return empty memory context."""
        return MemoryContext()
