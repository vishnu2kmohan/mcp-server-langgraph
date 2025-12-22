"""
Skills System

Implements Anthropic's Agent Skills specification for extending agent capabilities.

Skills are loaded from SKILL.md files with YAML frontmatter and provide:
- Reusable agent capabilities
- Sandboxed dependency installation
- Secure secret injection
- Progressive skill discovery

Usage:
    from mcp_server_langgraph.skills import SkillLoader, SkillRegistry, Skill

    loader = SkillLoader()
    skill = loader.load_from_path("/path/to/SKILL.md")

    registry = SkillRegistry()
    registry.register(skill)
"""

from mcp_server_langgraph.skills.discovery import SkillDiscovery
from mcp_server_langgraph.skills.executor import (
    ExecutionContext,
    ExecutionResult,
    SecretValidationResult,
    SkillExecutor,
)
from mcp_server_langgraph.skills.installer import (
    DependencyResolution,
    InstallationResult,
    SkillInstaller,
)
from mcp_server_langgraph.skills.loader import (
    SkillError,
    SkillLoader,
    SkillNotFoundError,
    SkillParseError,
    SkillValidationError,
)
from mcp_server_langgraph.skills.marketplace import (
    ANTHROPIC_MARKETPLACE,
    MarketplaceClient,
    MarketplaceConfig,
    MarketplaceRegistry,
)
from mcp_server_langgraph.skills import metrics
from mcp_server_langgraph.skills.auto_update import (
    AutoUpdateScheduler,
    SkillUpdate,
    SkillVersion,
    compare_versions,
)
from mcp_server_langgraph.skills.models import SandboxConfig, SecretVolume, Skill
from mcp_server_langgraph.skills.registry import SkillRegistry

__all__ = [
    # Models
    "Skill",
    "SandboxConfig",
    "SecretVolume",
    # Loader
    "SkillLoader",
    "SkillError",
    "SkillNotFoundError",
    "SkillParseError",
    "SkillValidationError",
    # Registry
    "SkillRegistry",
    # Discovery
    "SkillDiscovery",
    # Executor
    "SkillExecutor",
    "ExecutionResult",
    "ExecutionContext",
    "SecretValidationResult",
    # Marketplace
    "MarketplaceConfig",
    "MarketplaceRegistry",
    "MarketplaceClient",
    "ANTHROPIC_MARKETPLACE",
    # Installer
    "SkillInstaller",
    "InstallationResult",
    "DependencyResolution",
    # Metrics
    "metrics",
    # Auto-Update
    "AutoUpdateScheduler",
    "SkillVersion",
    "SkillUpdate",
    "compare_versions",
]
