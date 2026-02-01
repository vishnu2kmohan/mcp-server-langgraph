"""
Skills Bootstrap Module.

Initializes the skills system including:
- AutoUpdateScheduler for automatic skill updates
- Installed skills registration for version tracking
- MarketplaceRegistryAdapter for admin API compatibility

Usage:
    from mcp_server_langgraph.bootstrap.skills import init_skills

    skills_state = await init_skills(settings)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter

if TYPE_CHECKING:
    from mcp_server_langgraph.core.config import Settings
    from mcp_server_langgraph.skills.auto_update import AutoUpdateScheduler as SchedulerType
    from mcp_server_langgraph.skills.marketplace import MarketplaceClient, MarketplaceRegistry

logger = logging.getLogger(__name__)


class MarketplaceRegistryAdapter:
    """Adapter that wraps MarketplaceRegistry to implement the admin API Protocol.

    This adapter bridges the actual MarketplaceRegistry with the Protocol
    expected by the marketplace_admin router factory.
    """

    def __init__(self, registry: MarketplaceRegistry) -> None:
        """Initialize the adapter.

        Args:
            registry: The actual MarketplaceRegistry instance
        """
        self._registry = registry
        self._client: MarketplaceClient | None = None  # Lazy-loaded

    def _get_client(self) -> Any:
        """Get or create the MarketplaceClient with feature flag configuration."""
        if self._client is None:
            from mcp_server_langgraph.skills.marketplace import create_marketplace_client

            self._client = create_marketplace_client()
        return self._client

    def list_marketplaces(self) -> list[dict[str, Any]]:
        """List all registered marketplaces."""
        configs = self._registry.list_all()
        return [
            {
                "name": config.name,
                "uri": config.uri,
                "type": config.type,
                "trusted": config.trusted,
                "auto_sync": config.auto_sync,
                "requires_approval": config.requires_approval,
            }
            for config in configs
        ]

    def get_marketplace(self, name: str) -> dict[str, Any]:
        """Get details for a specific marketplace."""
        config = self._registry.get(name)
        if config is None:
            return {}
        return {
            "name": config.name,
            "uri": config.uri,
            "type": config.type,
            "trusted": config.trusted,
            "auto_sync": config.auto_sync,
            "requires_approval": config.requires_approval,
        }

    async def register_marketplace(
        self,
        name: str,
        uri: str,
        marketplace_type: str,
        trusted: bool,
        auto_sync: bool,
        required_approval: bool,
    ) -> bool:
        """Register a new marketplace."""
        from mcp_server_langgraph.skills.marketplace import MarketplaceConfig

        config = MarketplaceConfig(
            name=name,
            uri=uri,
            type=marketplace_type,  # type: ignore[arg-type]
            trusted=trusted,
            auto_sync=auto_sync,
            requires_approval=required_approval,
        )
        self._registry.register(config)
        return True

    async def remove_marketplace(self, name: str) -> bool:
        """Remove a marketplace."""
        self._registry.unregister(name)
        return True

    async def sync_marketplace(self, name: str) -> dict[str, int]:
        """Sync skills from a marketplace."""
        config = self._registry.get(name)
        if config is None:
            return {"synced": 0, "new": 0, "updated": 0}

        client = self._get_client()
        skills = await client.list_skills(config)
        return {"synced": len(skills), "new": 0, "updated": 0}

    def list_skills(self, marketplace_name: str) -> list[dict[str, Any]]:
        """List skills from a specific marketplace."""
        # This is a synchronous method but needs async fetch
        # For now, return empty list - async version should be used
        return []


def create_marketplace_admin_router() -> tuple[APIRouter, MarketplaceRegistryAdapter]:
    """Create the marketplace admin router with a real registry adapter.

    Returns:
        Tuple of (router, adapter) for registration
    """
    from mcp_server_langgraph.api.v1.marketplace_admin import create_marketplace_router
    from mcp_server_langgraph.skills.marketplace import MarketplaceRegistry

    registry = MarketplaceRegistry()
    adapter = MarketplaceRegistryAdapter(registry)
    router = create_marketplace_router(adapter)

    return router, adapter


@dataclass
class SkillsState:
    """State container for skills system components.

    Attributes:
        auto_update_scheduler: The AutoUpdateScheduler instance, or None if disabled
        installed_skills: List of skill names loaded from disk
        marketplace_router: The marketplace admin API router (for registration in app.py)
        marketplace_adapter: The registry adapter for marketplace operations
        skill_search_tool: The SkillSearchTool for semantic search, or None if disabled
    """

    auto_update_scheduler: Any | None = None
    installed_skills: list[str] = field(default_factory=list)
    marketplace_router: APIRouter | None = None
    marketplace_adapter: MarketplaceRegistryAdapter | None = None
    skill_search_tool: Any | None = None

    async def cleanup(self) -> None:
        """Stop the auto-update scheduler if running."""
        if self.auto_update_scheduler is not None:
            try:
                await self.auto_update_scheduler.stop()
                logger.info("AutoUpdateScheduler stopped")
            except Exception as e:
                logger.warning(f"Error stopping AutoUpdateScheduler: {e}")


async def init_skills(settings: Settings) -> SkillsState:
    """Initialize the skills system.

    This function:
    1. Checks if skills marketplace is enabled via feature flag
    2. Initializes the AutoUpdateScheduler if enabled
    3. Registers installed skills for version tracking
    4. Creates the marketplace admin API router
    5. Creates SkillSearchTool for semantic search if enabled

    Args:
        settings: Application settings

    Returns:
        SkillsState with initialized components
    """
    from mcp_server_langgraph.core.feature_flags import feature_flags
    from mcp_server_langgraph.skills.adapters import create_skill_search_tool
    from mcp_server_langgraph.skills.auto_update import (
        AutoUpdateScheduler,
        is_auto_update_enabled,
    )
    from mcp_server_langgraph.skills.installer import SkillInstaller

    scheduler: SchedulerType | None = None
    installed_skills: list[str] = []
    marketplace_router: APIRouter | None = None
    marketplace_adapter: MarketplaceRegistryAdapter | None = None
    skill_search_tool: Any | None = None

    # Create SkillSearchTool for semantic search if enabled
    if feature_flags.enable_semantic_skill_search:
        try:
            skill_search_tool = create_skill_search_tool()
            if skill_search_tool:
                logger.info("SkillSearchTool created for semantic skill search")
            else:
                logger.debug("SkillSearchTool not created (missing configuration)")
        except Exception as e:
            logger.warning(f"Failed to create SkillSearchTool: {e}")
            skill_search_tool = None

    # Check if skills marketplace auto-update is enabled
    if is_auto_update_enabled():
        try:
            # Create and start the scheduler
            scheduler = AutoUpdateScheduler(
                update_interval_hours=24,  # Check for updates daily
                auto_apply=False,  # Require manual approval for updates
            )
            await scheduler.start()
            logger.info("AutoUpdateScheduler started (interval: 24h)")

            # Register installed skills for version tracking
            installer = SkillInstaller(skill_search_tool=skill_search_tool)
            installed_skills = installer.list_installed()

            for skill_name in installed_skills:
                # Register with default version tracking
                # Actual version is read from SKILL.md when needed
                scheduler.register_installed_skill(
                    skill_name=skill_name,
                    version="unknown",  # Will be updated on first check
                    marketplace="local",
                )

            logger.info(f"Registered {len(installed_skills)} installed skills")

        except Exception as e:
            logger.warning(f"Failed to initialize skills auto-update: {e}")
            scheduler = None
    else:
        logger.debug("Skills marketplace auto-update disabled by feature flag")

    # Create the marketplace admin router (always created, feature flag checked at endpoint level)
    try:
        marketplace_router, marketplace_adapter = create_marketplace_admin_router()
        logger.info("Marketplace admin router created")
    except Exception as e:
        logger.warning(f"Failed to create marketplace admin router: {e}")

    return SkillsState(
        auto_update_scheduler=scheduler,
        installed_skills=installed_skills,
        marketplace_router=marketplace_router,
        marketplace_adapter=marketplace_adapter,
        skill_search_tool=skill_search_tool,
    )
