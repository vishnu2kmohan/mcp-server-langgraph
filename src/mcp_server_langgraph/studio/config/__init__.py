"""STUDIO.md configuration models and parsing.

This module provides Pydantic models for parsing and validating STUDIO.md
configuration files, which define hierarchical capability settings for
the agent studio environment.

Key Components:
- StudioConfig: Main configuration model
- StudioToolsConfig: Tool enablement/disablement
- StudioSkillsConfig: Skill enablement/categories
- StudioMemoryConfig: Memory tier configuration
- StudioCostConfig: Cost control limits
- StudioModelsConfig: Model selection/blocking
- StudioRule: Policy rules

Usage:
    from mcp_server_langgraph.studio.config import StudioConfig

    config = StudioConfig(
        name="My Project",
        tools=StudioToolsConfig(enabled=["file_reader"]),
        skills=StudioSkillsConfig(enabled=["summarize"]),
    )

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from mcp_server_langgraph.studio.config.models import (
    StudioConfig,
    StudioCostConfig,
    StudioMemoryConfig,
    StudioModelsConfig,
    StudioRule,
    StudioSkillsConfig,
    StudioToolsConfig,
)

__all__ = [
    "StudioConfig",
    "StudioCostConfig",
    "StudioMemoryConfig",
    "StudioModelsConfig",
    "StudioRule",
    "StudioSkillsConfig",
    "StudioToolsConfig",
]
