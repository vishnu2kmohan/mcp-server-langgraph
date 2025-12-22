"""
Thinking Budget (Hybrid Approach).

Phase 6 of the Multi-Agent Orchestrator Enhancement Plan.

Provides unified thinking levels across models:
- Claude Opus 4.5: Uses native `effort` parameter (low, medium, high)
- Other models: Uses `thinking_budget` token count

Thinking Levels:
| Level  | Claude Opus 4.5 | Other Models |
|--------|-----------------|--------------|
| LOW    | effort: "low"   | 1,024 tokens |
| MEDIUM | effort: "medium"| 8,192 tokens |
| HIGH   | effort: "high"  | 32,768 tokens|
| ULTRA  | effort: "high"  | 65,536 tokens|

Usage:
    from mcp_server_langgraph.agents.thinking_budget import (
        ThinkingBudgetManager,
        ThinkingLevel,
    )

    manager = ThinkingBudgetManager()
    params = manager.get_params("claude-opus-4-5-20251101", ThinkingLevel.HIGH)
    # Returns: {"effort": "high"}

    params = manager.get_params("gemini-3-flash", ThinkingLevel.HIGH)
    # Returns: {"thinking_budget": 32768}
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from mcp_server_langgraph.agents.model_registry import (
    ModelRegistry,
    get_default_registry,
)
from mcp_server_langgraph.core.feature_flags import feature_flags

if TYPE_CHECKING:
    pass


class ThinkingLevel(Enum):
    """Thinking effort levels.

    Unified levels that map to model-specific parameters.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


class ThinkingBudgetManager:
    """Manages thinking budgets across different models.

    Implements hybrid approach:
    - Claude Opus 4.5: Uses native effort parameter
    - Other models: Uses thinking_budget token count

    Usage:
        manager = ThinkingBudgetManager()

        # Get params for a specific model and level
        params = manager.get_params("claude-opus-4-5-20251101", ThinkingLevel.HIGH)
        # -> {"effort": "high"}

        params = manager.get_params("gemini-3-flash", ThinkingLevel.HIGH)
        # -> {"thinking_budget": 32768}
    """

    # Token budgets for non-effort models
    TOKEN_BUDGETS: dict[ThinkingLevel, int] = {
        ThinkingLevel.LOW: 1024,
        ThinkingLevel.MEDIUM: 8192,
        ThinkingLevel.HIGH: 32768,
        ThinkingLevel.ULTRA: 65536,
    }

    # Effort parameter mapping for Opus
    EFFORT_MAPPING: dict[ThinkingLevel, str] = {
        ThinkingLevel.LOW: "low",
        ThinkingLevel.MEDIUM: "medium",
        ThinkingLevel.HIGH: "high",
        ThinkingLevel.ULTRA: "high",  # ULTRA maps to high (max available)
    }

    def __init__(self, model_registry: ModelRegistry | None = None) -> None:
        """Initialize ThinkingBudgetManager.

        Args:
            model_registry: ModelRegistry for capability lookup.
                Defaults to the global registry.
        """
        self.model_registry = model_registry or get_default_registry()

    def get_params(self, model: str, level: ThinkingLevel) -> dict[str, str | int]:
        """Get model-specific thinking parameters.

        Args:
            model: Model identifier
            level: Desired thinking level

        Returns:
            Dict with either:
            - {"effort": "low"|"medium"|"high"} for Opus
            - {"thinking_budget": <tokens>} for other models
        """
        if self.supports_effort_param(model):
            # Opus: Use native effort parameter
            return {"effort": self.EFFORT_MAPPING[level]}
        else:
            # Other models: Use thinking_budget token count
            return {"thinking_budget": self.TOKEN_BUDGETS[level]}

    def supports_effort_param(self, model: str) -> bool:
        """Check if model supports native effort parameter.

        Args:
            model: Model identifier

        Returns:
            True if model supports effort param (currently only Claude Opus 4.5)
        """
        caps = self.model_registry.get(model)
        return caps.supports_effort_param

    def get_default_level(self) -> ThinkingLevel:
        """Get configured default thinking level.

        Returns:
            ThinkingLevel from feature flags (default: MEDIUM)
        """
        return self.level_from_string(feature_flags.default_thinking_level)

    def level_from_string(self, level_str: str) -> ThinkingLevel:
        """Convert string to ThinkingLevel.

        Args:
            level_str: Level as string (case insensitive)

        Returns:
            Corresponding ThinkingLevel, defaults to MEDIUM if invalid
        """
        level_str = level_str.lower().strip()
        for level in ThinkingLevel:
            if level.value == level_str:
                return level
        return ThinkingLevel.MEDIUM  # Default fallback
