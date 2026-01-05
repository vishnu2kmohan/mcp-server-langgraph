"""StudioConfig Pydantic models for STUDIO.md configuration.

These models define the schema for STUDIO.md configuration files,
enabling hierarchical capability configuration across enterprise→task scopes.

Each model section (tools, skills, memory, cost, models, rules) can be
configured at any scope level, with lower scopes overriding higher ones.

Usage:
    from mcp_server_langgraph.studio.config.models import (
        StudioConfig,
        StudioToolsConfig,
        StudioSkillsConfig,
    )

    config = StudioConfig(
        name="My Project",
        tools=StudioToolsConfig(enabled=["file_reader"]),
    )

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from mcp_server_langgraph.core.scopes import CapabilityScope


class StudioToolsConfig(BaseModel):
    """Configuration for tool enablement and disablement.

    Tools listed in 'enabled' are made available at this scope.
    Tools listed in 'disabled' are blocked even if enabled at higher scopes.

    Attributes:
        enabled: List of tool names to enable
        disabled: List of tool names to disable
        allow_all: If True, enable all tools except those in disabled
    """

    model_config = {"extra": "ignore"}

    enabled: list[str] = Field(default_factory=list)
    disabled: list[str] = Field(default_factory=list)
    allow_all: bool = False


class StudioSkillsConfig(BaseModel):
    """Configuration for skill enablement and categories.

    Skills listed in 'enabled' are made available at this scope.
    Skills listed in 'disabled' are blocked even if enabled at higher scopes.
    Categories can be used to enable groups of skills.

    Attributes:
        enabled: List of skill names to enable
        disabled: List of skill names to disable
        categories: List of skill categories to enable (e.g., "text", "code")
        allow_all: If True, enable all skills except those in disabled
    """

    model_config = {"extra": "ignore"}

    enabled: list[str] = Field(default_factory=list)
    disabled: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    allow_all: bool = False


class StudioMemoryConfig(BaseModel):
    """Configuration for memory tiers and limits.

    Controls which memory tiers are available and their limits.

    Attributes:
        enabled: Whether memory is enabled at this scope
        tiers: List of enabled memory tiers (working, session, durable)
        max_items: Maximum number of items to retrieve
        ttl_seconds: TTL for session memory in seconds
    """

    model_config = {"extra": "ignore"}

    enabled: bool = True
    tiers: list[str] = Field(default_factory=lambda: ["working", "session"])
    max_items: int = 50
    ttl_seconds: int = 3600


class StudioCostConfig(BaseModel):
    """Configuration for cost controls and limits.

    Sets token and cost limits for this scope to prevent budget overruns.

    Attributes:
        max_tokens: Maximum tokens per request
        max_cost: Maximum cost in USD per request
        budget_alert_threshold: Threshold (0-1) for budget alerts
        daily_limit: Daily cost limit in USD
        monthly_limit: Monthly cost limit in USD
    """

    model_config = {"extra": "ignore"}

    max_tokens: int | None = None
    max_cost: float | None = None
    budget_alert_threshold: float = 0.8
    daily_limit: float | None = None
    monthly_limit: float | None = None


class StudioModelsConfig(BaseModel):
    """Configuration for model selection and restrictions.

    Controls which models are available at this scope.

    Attributes:
        default_model: Default model ID for this scope
        allowed_models: List of allowed model IDs (empty = all allowed)
        blocked_models: List of blocked model IDs
        tier_overrides: Mapping of complexity tier to model ID
    """

    model_config = {"extra": "ignore"}

    default_model: str | None = None
    allowed_models: list[str] = Field(default_factory=list)
    blocked_models: list[str] = Field(default_factory=list)
    tier_overrides: dict[str, str] = Field(default_factory=dict)


class StudioRule(BaseModel):
    """A policy rule for agent behavior.

    Rules define behavioral constraints that agents must follow.
    They can be informational, warnings, or errors.

    Attributes:
        name: Unique identifier for the rule
        description: Human-readable description of the rule
        severity: Severity level (info, warning, error)
        pattern: Optional regex pattern for detection
        action: Action to take when triggered (log, warn, block)
    """

    model_config = {"extra": "ignore"}

    name: str
    description: str
    severity: Literal["info", "warning", "error"] = "warning"
    pattern: str | None = None
    action: Literal["log", "warn", "block"] = "warn"


class StudioConfig(BaseModel):
    """Main STUDIO.md configuration model.

    Represents a complete STUDIO.md configuration file with all sections.
    This is the top-level model that aggregates all configuration options.

    Attributes:
        name: Name of the configuration (required)
        description: Description of the configuration
        version: Version string for the configuration
        scope: The CapabilityScope this config applies to
        tools: Tool configuration section
        skills: Skill configuration section
        memory: Memory configuration section
        cost: Cost control section
        models: Model selection section
        rules: List of policy rules
        instructions: Markdown instructions for agents
        extends: Parent config to extend (for inheritance)
    """

    model_config = {"extra": "ignore"}

    name: str
    description: str | None = None
    version: str = "1.0.0"
    scope: CapabilityScope | None = None
    tools: StudioToolsConfig | None = None
    skills: StudioSkillsConfig | None = None
    memory: StudioMemoryConfig | None = None
    cost: StudioCostConfig | None = None
    models: StudioModelsConfig | None = None
    rules: list[StudioRule] | None = None
    instructions: str | None = None
    extends: str | None = None

    def __init__(self, **data: object) -> None:
        """Initialize with default scope."""
        super().__init__(**data)
        if self.scope is None:
            from mcp_server_langgraph.core.scopes import CapabilityScope

            object.__setattr__(self, "scope", CapabilityScope.PROJECT)
