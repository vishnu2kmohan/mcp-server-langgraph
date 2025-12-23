"""
Short-Form Tool Descriptions.

Phase 3.1 of the Multi-Agent Orchestrator Enhancement Plan.

Provides three levels of tool description detail to optimize
token usage based on available context budget:
- short: ~10 tokens (minimal, just the action)
- medium: ~50 tokens (+ parameters summary)
- full: ~150 tokens (+ examples, rate limits, edge cases)

Expected token savings: ~40% when using short descriptions.

Usage:
    from mcp_server_langgraph.mcp.tool_descriptions import (
        ToolDescription,
        ToolDescriptionRegistry,
        get_detail_level,
    )

    registry = ToolDescriptionRegistry()
    registry.register(ToolDescription(
        name="chat",
        description_short="Chat with AI agent",
        description_medium="Chat with AI agent. Supports text and files.",
        description_full="Chat with AI agent. Supports text messages, "
            "file attachments, and streaming. Rate limited to 100/min.",
    ))

    # Get description based on context usage
    level = get_detail_level(context_usage=0.7)  # Returns "short"
    desc = registry.get_description("chat", level)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    pass


# Type alias for description levels
DescriptionLevel = Literal["minimal", "short", "medium", "full"]


@dataclass
class ToolDescription:
    """Multi-level tool description for context-aware token optimization.

    Provides three levels of description detail:
    - short: Minimal description (~10 tokens)
    - medium: Standard description with parameters (~50 tokens)
    - full: Comprehensive with examples and limits (~150 tokens)

    Usage:
        desc = ToolDescription(
            name="search",
            description_short="Search documents",
            description_medium="Search documents by query. Returns top 10 results.",
            description_full="Search documents by query. Supports full-text search, "
                "filtering by date and type. Returns top 10 results. "
                "Rate limited to 30 requests per minute.",
        )
        text = desc.get_description("short")  # Returns "Search documents"
    """

    name: str
    description_short: str
    description_medium: str
    description_full: str

    # Approximate chars per token (conservative estimate)
    CHARS_PER_TOKEN: int = field(default=4, repr=False)

    def get_description(self, level: DescriptionLevel = "short") -> str:
        """Get description at specified level.

        Args:
            level: Description level (minimal, short, medium, full).
                Defaults to "short" for optimal token savings.

        Returns:
            Description text at the requested level.
        """
        if level == "minimal":
            # For minimal, just return name as description
            return self.name
        elif level == "short":
            return self.description_short
        elif level == "medium":
            return self.description_medium
        elif level == "full":
            return self.description_full
        else:
            # Default to short for unknown levels
            return self.description_short  # type: ignore[unreachable]

    def estimate_tokens(self, level: DescriptionLevel = "short") -> int:
        """Estimate token count for description at level.

        Args:
            level: Description level to estimate.

        Returns:
            Estimated token count.
        """
        text = self.get_description(level)
        return len(text) // self.CHARS_PER_TOKEN

    def savings_percentage(self, from_level: DescriptionLevel, to_level: DescriptionLevel) -> float:
        """Calculate percentage savings between levels.

        Args:
            from_level: Shorter level (e.g., "short")
            to_level: Longer level (e.g., "full")

        Returns:
            Percentage of tokens saved (0-100).
        """
        from_tokens = self.estimate_tokens(from_level)
        to_tokens = self.estimate_tokens(to_level)

        if to_tokens == 0:
            return 0.0

        saved = to_tokens - from_tokens
        return (saved / to_tokens) * 100


class ToolDescriptionRegistry:
    """Registry for tool descriptions.

    Manages a collection of tool descriptions and provides
    lookup by tool name and level.

    Usage:
        registry = ToolDescriptionRegistry()
        registry.register(ToolDescription(...))
        desc = registry.get_description("tool_name", "short")
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._descriptions: dict[str, ToolDescription] = {}

    def register(self, description: ToolDescription) -> None:
        """Register a tool description.

        Args:
            description: ToolDescription to register.
        """
        self._descriptions[description.name] = description

    def get(self, name: str) -> ToolDescription | None:
        """Get tool description by name.

        Args:
            name: Tool name.

        Returns:
            ToolDescription if found, None otherwise.
        """
        return self._descriptions.get(name)

    def get_description(self, name: str, level: DescriptionLevel = "short") -> str | None:
        """Get description text for a tool at specified level.

        Args:
            name: Tool name.
            level: Description level.

        Returns:
            Description text if found, None otherwise.
        """
        desc = self.get(name)
        if desc is None:
            return None
        return desc.get_description(level)

    def list_tools(self) -> list[str]:
        """List all registered tool names.

        Returns:
            List of tool names.
        """
        return list(self._descriptions.keys())


def get_detail_level(context_usage: float) -> DescriptionLevel:
    """Determine appropriate description level based on context usage.

    Maps context window usage percentage to description level:
    - 0-30% used: "full" (plenty of room for details)
    - 30-60% used: "medium" (moderate details)
    - 60-90% used: "short" (conserve tokens)
    - 90%+ used: "minimal" (critical conservation)

    Args:
        context_usage: Percentage of context window used (0.0 to 1.0).

    Returns:
        Appropriate description level.
    """
    if context_usage < 0.30:
        return "full"
    elif context_usage < 0.60:
        return "medium"
    elif context_usage < 0.90:
        return "short"
    else:
        return "minimal"


# Default registry instance
_default_registry: ToolDescriptionRegistry | None = None


def get_default_registry() -> ToolDescriptionRegistry:
    """Get the default tool description registry.

    Returns:
        Default ToolDescriptionRegistry instance.
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = ToolDescriptionRegistry()
    return _default_registry
