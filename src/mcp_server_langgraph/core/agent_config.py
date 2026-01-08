"""
Agent Configuration - Compile-Time Graph Composition.

This module provides an immutable configuration class for agent graph topology.
It replaces runtime feature flag checks with compile-time composition, following
the Open/Closed Principle.

Key benefits:
1. Graph topology is determined at compile time (graph construction)
2. Checkpoint compatibility via graph_version hash
3. Testable configuration without modifying node functions
4. Clear separation of topology-affecting vs behavior-affecting settings

Usage:
    from mcp_server_langgraph.core.agent_config import AgentConfig

    # Create with defaults
    config = AgentConfig()

    # Create from Settings
    config = AgentConfig.from_settings(settings)

    # Get graph version for checkpoint compatibility
    version = config.graph_version
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_server_langgraph.core.config import Settings


# Fields that affect graph topology (nodes/edges)
# Changes to these fields require a different graph version
_TOPOLOGY_FIELDS: frozenset[str] = frozenset(
    {
        "enable_context_compaction",
        "enable_verification",
        "enable_visual_verification",
        "enable_dynamic_context_loading",
        "enable_checkpointing",
        "enable_tool_calling",
        "enable_semantic_tool_selection",
    }
)


@dataclass(frozen=True)
class AgentConfig:
    """
    Immutable configuration that determines agent graph topology.

    This class captures all settings that affect graph structure (nodes, edges).
    Settings that only affect behavior within nodes are also included for
    convenience but don't affect the graph_version hash.

    The frozen=True makes this immutable, ensuring graph topology can't change
    after construction. This is essential for checkpoint compatibility.
    """

    # Context Management
    enable_context_compaction: bool = True
    compaction_threshold: int = 8000
    target_after_compaction: int = 4000
    recent_message_count: int = 5

    # Verification (LLM-as-judge)
    enable_verification: bool = True
    verification_quality_threshold: float = 0.7
    max_refinement_attempts: int = 3

    # Visual Verification (screenshot-based UI verification)
    enable_visual_verification: bool = False
    visual_verification_text_weight: float = 0.6
    visual_verification_visual_weight: float = 0.4
    visual_verification_max_urls: int = 3  # Max URLs to verify per response
    visual_verification_url_priority: str = "last"  # "first", "last", or "all"

    # Dynamic Context Loading
    enable_dynamic_context_loading: bool = False

    # Parallel Execution
    enable_parallel_execution: bool = False
    max_parallel_tools: int = 5

    # Tool Calling (bind tools to LLM for autonomous tool invocation)
    # When enabled, tools are bound to the model so the LLM can generate tool_calls
    # This enables true agentic behavior where the LLM decides when to use tools
    enable_tool_calling: bool = True

    # Semantic Tool Selection (adds select_tools node for dynamic tool binding)
    # When enabled, uses semantic search to select relevant tools based on query
    # before binding them to the LLM. Reduces token usage with many tools (50+).
    enable_semantic_tool_selection: bool = False
    max_selected_tools: int = 10
    semantic_tool_search_threshold: float = 0.5

    # Checkpointing
    enable_checkpointing: bool = True

    # Interrupt Checking (Claude Agent SDK pattern)
    enable_interrupt_checking: bool = True

    @property
    def graph_version(self) -> str:
        """
        Deterministic hash of config fields that affect graph topology.

        This version is used to validate checkpoint compatibility. If two
        configs have different graph_version values, their graphs have
        different structures and checkpoints are not compatible.

        Returns:
            8-character hex hash prefix
        """
        # Only include topology-affecting fields in the hash
        topology_values = (
            self.enable_context_compaction,
            self.enable_verification,
            self.enable_visual_verification,
            self.enable_dynamic_context_loading,
            self.enable_checkpointing,
            self.enable_tool_calling,
            self.enable_semantic_tool_selection,
        )
        hash_input = str(topology_values).encode()
        return sha256(hash_input).hexdigest()[:8]

    @property
    def topology_fields(self) -> frozenset[str]:
        """
        Return the set of field names that affect graph topology.

        This is useful for documentation and testing.
        """
        return _TOPOLOGY_FIELDS

    @classmethod
    def from_settings(cls, settings: Settings) -> AgentConfig:
        """
        Create AgentConfig from a Settings object.

        Extracts relevant settings fields and creates an immutable config.

        Args:
            settings: Application Settings object

        Returns:
            AgentConfig with values from settings
        """
        return cls(
            # Context Management
            enable_context_compaction=getattr(settings, "enable_context_compaction", True),
            compaction_threshold=getattr(settings, "compaction_threshold", 8000),
            target_after_compaction=getattr(settings, "target_after_compaction", 4000),
            recent_message_count=getattr(settings, "recent_message_count", 5),
            # Verification
            enable_verification=getattr(settings, "enable_verification", True),
            verification_quality_threshold=getattr(settings, "verification_quality_threshold", 0.7),
            max_refinement_attempts=getattr(settings, "max_refinement_attempts", 3),
            # Visual Verification
            enable_visual_verification=getattr(settings, "enable_visual_verification", False),
            visual_verification_text_weight=getattr(settings, "visual_verification_text_weight", 0.6),
            visual_verification_visual_weight=getattr(settings, "visual_verification_visual_weight", 0.4),
            visual_verification_max_urls=getattr(settings, "visual_verification_max_urls", 3),
            visual_verification_url_priority=getattr(settings, "visual_verification_url_priority", "last"),
            # Dynamic Context
            enable_dynamic_context_loading=getattr(settings, "enable_dynamic_context_loading", False),
            # Parallel Execution
            enable_parallel_execution=getattr(settings, "enable_parallel_execution", False),
            max_parallel_tools=getattr(settings, "max_parallel_tools", 5),
            # Tool Calling
            enable_tool_calling=getattr(settings, "enable_tool_calling", True),
            # Semantic Tool Selection
            enable_semantic_tool_selection=getattr(settings, "enable_semantic_tool_selection", False),
            max_selected_tools=getattr(settings, "max_selected_tools", 10),
            semantic_tool_search_threshold=getattr(settings, "semantic_tool_search_threshold", 0.5),
            # Checkpointing
            enable_checkpointing=getattr(settings, "enable_checkpointing", True),
            # Interrupt Checking
            enable_interrupt_checking=getattr(settings, "enable_interrupt_checking", True),
        )


__all__ = ["AgentConfig"]
