"""HierarchicalCapabilityProvider for scope-based capability resolution.

Implements the CapabilityProvider protocol to provide unified resolution
of tools, skills, and memory based on capability scope hierarchy.

This is the main orchestration point that ties together:
- HierarchicalToolRegistry for tool resolution
- HierarchicalSkillRegistry for skill resolution
- MemoryStore for memory retrieval
- StudioLoader for STUDIO.md configuration (optional)

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from mcp_server_langgraph.capabilities.provider import (
    MemoryContext,
    SkillSpec,
    ToolSpec,
)
from mcp_server_langgraph.core.scopes import CapabilityScope
from mcp_server_langgraph.memory.store import MemoryStore
from mcp_server_langgraph.skills.hierarchical import HierarchicalSkillRegistry
from mcp_server_langgraph.tools.hierarchical import HierarchicalToolRegistry


class HierarchicalCapabilityProvider:
    """Hierarchical capability provider implementing CapabilityProvider protocol.

    Resolves tools, skills, and memory based on scope hierarchy, delegating
    to appropriate registries and stores.

    Attributes:
        tool_registry: Registry for hierarchical tool lookup
        skill_registry: Registry for hierarchical skill lookup
        memory_store: Store for hierarchical memory retrieval
    """

    def __init__(
        self,
        tool_registry: HierarchicalToolRegistry | None = None,
        skill_registry: HierarchicalSkillRegistry | None = None,
        memory_store: MemoryStore | None = None,
    ) -> None:
        """Initialize the hierarchical capability provider.

        Args:
            tool_registry: Optional tool registry for tool resolution
            skill_registry: Optional skill registry for skill resolution
            memory_store: Optional memory store for memory retrieval
        """
        self.tool_registry = tool_registry or HierarchicalToolRegistry()
        self.skill_registry = skill_registry or HierarchicalSkillRegistry()
        self.memory_store = memory_store or MemoryStore()

    async def get_tools(
        self,
        scope: CapabilityScope,
        names: list[str] | None = None,
    ) -> list[ToolSpec]:
        """Get tools available at the specified scope.

        Resolves tools from the hierarchical tool registry, optionally
        filtering by name.

        Args:
            scope: Capability scope for resolution
            names: Optional list of tool names to filter by

        Returns:
            List of ToolSpec objects
        """
        if names is not None:
            # Get specific tools by name
            tools: list[ToolSpec] = []
            for name in names:
                tool = self.tool_registry.get_for_scope(name, scope)
                if tool is not None:
                    tools.append(tool)
            return tools
        else:
            # Get all tools at this scope
            return self.tool_registry.list_for_scope(scope, include_parent_scopes=True)

    async def get_skills(
        self,
        scope: CapabilityScope,
        names: list[str] | None = None,
    ) -> list[SkillSpec]:
        """Get skills available at the specified scope.

        Resolves skills from the hierarchical skill registry, optionally
        filtering by name. Converts Skill objects to SkillSpec for the
        protocol interface.

        Args:
            scope: Capability scope for resolution
            names: Optional list of skill names to filter by

        Returns:
            List of SkillSpec objects
        """
        if names is not None:
            # Get specific skills by name
            skills: list[SkillSpec] = []
            for name in names:
                skill = self.skill_registry.get_for_scope(name, scope)
                if skill is not None:
                    # Convert Skill to SkillSpec
                    skills.append(
                        SkillSpec(
                            name=skill.name,
                            description=skill.description,
                            category=getattr(skill, "category", None),
                            tags=getattr(skill, "tags", None),
                            scope=scope,
                        )
                    )
            return skills
        else:
            # Get all skills at this scope
            registry_skills = self.skill_registry.list_for_scope(scope, include_parent_scopes=True)
            return [
                SkillSpec(
                    name=s.name,
                    description=s.description,
                    category=getattr(s, "category", None),
                    tags=getattr(s, "tags", None),
                    scope=scope,
                )
                for s in registry_skills
            ]

    async def get_memory(
        self,
        scope: CapabilityScope,
        query: str | None = None,
    ) -> MemoryContext:
        """Get memory context for the specified scope.

        Retrieves relevant memories from the memory store based on
        the query and scope.

        Args:
            scope: Capability scope for memory retrieval
            query: Optional query for semantic retrieval

        Returns:
            MemoryContext with retrieved memories
        """
        relevant_memories: list[Any] = []

        if query and self.memory_store:
            # Perform semantic search
            results = await self.memory_store.get_relevant(
                query=query,
                scope=scope,
                limit=5,
            )
            relevant_memories = [
                {
                    "id": r.id,
                    "content": r.content,
                    "score": r.score,
                    "tier": r.tier.value,
                }
                for r in results
            ]

        return MemoryContext(
            working_memory={},
            session_memory=[],
            durable_memory=[],
            relevant_memories=relevant_memories,
        )

    async def resolve(self, request: Any) -> ResolvedCapabilities:
        """Resolve all capabilities for a request.

        Combines tools, skills, and memory based on request scope and
        merge strategy.

        Args:
            request: AgentRequest with capability fields

        Returns:
            ResolvedCapabilities with resolved tools, skills, and memory
        """
        scope = getattr(request, "scope", CapabilityScope.PROJECT)
        tool_names = getattr(request, "tools", None)
        skill_names = getattr(request, "skills", None)

        tools = await self.get_tools(scope=scope, names=tool_names)
        skills = await self.get_skills(scope=scope, names=skill_names)

        return ResolvedCapabilities(
            tools=tools,
            skills=skills,
            scope=scope,
        )


@dataclass
class ResolvedCapabilities:
    """Result of capability resolution.

    Attributes:
        tools: Resolved tool specifications
        skills: Resolved skill specifications
        scope: The scope used for resolution
        memory: Optional memory context
    """

    tools: list[ToolSpec] = field(default_factory=list)
    skills: list[SkillSpec] = field(default_factory=list)
    scope: CapabilityScope = CapabilityScope.PROJECT
    memory: MemoryContext | None = None


MergeStrategy = Literal["union", "intersection", "user_only", "router_only"]


def merge_capabilities(
    router_tools: list[str],
    user_tools: list[str],
    strategy: MergeStrategy = "union",
) -> list[str]:
    """Merge router-recommended and user-selected capabilities.

    Args:
        router_tools: Tools recommended by the router
        user_tools: Tools selected by the user
        strategy: Merge strategy to use

    Returns:
        Merged list of tool names

    Strategies:
        - union: Include all tools from both sources
        - intersection: Include only tools in both sources
        - user_only: Include only user-selected tools
        - router_only: Include only router-recommended tools
    """
    if strategy == "union":
        return list(set(router_tools) | set(user_tools))
    elif strategy == "intersection":
        return list(set(router_tools) & set(user_tools))
    elif strategy == "user_only":
        return list(user_tools)
    else:  # strategy == "router_only"
        return list(router_tools)
