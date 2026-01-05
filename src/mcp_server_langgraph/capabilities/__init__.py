"""Capability management for hierarchical tool/skill resolution.

This module provides the core abstractions for the Hierarchical Capability
Architecture (ADR-0092), enabling all agents to be tool-aware and skill-aware
via composition rather than inheritance.

Key Components:
- CapabilityProvider: Protocol for resolving tools, skills, and memory
- ToolSpec, SkillSpec, MemoryContext: Data types for capabilities
- ResolvedCapabilities: Container for resolved capabilities
- NullCapabilityProvider: No-op implementation for backward compatibility

Usage:
    from mcp_server_langgraph.capabilities import (
        CapabilityProvider,
        ResolvedCapabilities,
        ToolSpec,
        SkillSpec,
        MemoryContext,
        NullCapabilityProvider,
    )

    # Inject provider into agent
    agent = WorkerAgent(llm_factory, capability_provider=provider)

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from mcp_server_langgraph.capabilities.provider import (
    CapabilityProvider,
    MemoryContext,
    NullCapabilityProvider,
    ResolvedCapabilities,
    SkillSpec,
    ToolSpec,
)

__all__ = [
    "CapabilityProvider",
    "MemoryContext",
    "NullCapabilityProvider",
    "ResolvedCapabilities",
    "SkillSpec",
    "ToolSpec",
]
