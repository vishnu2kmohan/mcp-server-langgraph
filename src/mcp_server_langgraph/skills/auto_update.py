"""
Skills Auto-Update Module.

Provides automatic synchronization of skills from configured marketplaces.
Supports version tracking, update notifications, and auto-apply options.

Usage:
    from mcp_server_langgraph.skills.auto_update import AutoUpdateScheduler

    scheduler = AutoUpdateScheduler(update_interval_hours=24, auto_apply=False)
    await scheduler.start()
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from mcp_server_langgraph.skills.marketplace import MarketplaceConfig, MarketplaceRegistry

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# =============================================================================
# Models
# =============================================================================


class SkillVersion(BaseModel):
    """Tracks installed skill version information."""

    skill_name: str = Field(description="Name of the skill")
    version: str = Field(description="Installed version")
    marketplace: str = Field(description="Source marketplace")
    installed_at: datetime = Field(description="Installation timestamp")
    last_checked: datetime | None = Field(default=None, description="Last update check")


class SkillUpdate(BaseModel):
    """Represents an available skill update."""

    skill_name: str
    current_version: str
    new_version: str
    marketplace: str
    changelog: str | None = None


# =============================================================================
# Version Comparison
# =============================================================================


def compare_versions(version1: str, version2: str) -> int:
    """Compare two semantic version strings.

    Args:
        version1: First version string (e.g., "1.0.0")
        version2: Second version string (e.g., "1.0.1")

    Returns:
        -1 if version1 < version2
         0 if version1 == version2
         1 if version1 > version2
    """
    v1_parts = [int(x) for x in version1.split(".")]
    v2_parts = [int(x) for x in version2.split(".")]

    # Pad shorter version with zeros
    while len(v1_parts) < len(v2_parts):
        v1_parts.append(0)
    while len(v2_parts) < len(v1_parts):
        v2_parts.append(0)

    for v1, v2 in zip(v1_parts, v2_parts, strict=True):
        if v1 < v2:
            return -1
        if v1 > v2:
            return 1

    return 0


# =============================================================================
# Metrics
# =============================================================================


def record_skill_update_metric(
    skill_name: str,
    old_version: str,
    new_version: str,
    success: bool,
) -> None:
    """Record skill update metric.

    Args:
        skill_name: Name of the skill updated
        old_version: Previous version
        new_version: New version
        success: Whether update succeeded
    """
    logger.info(
        "skill_update",
        extra={
            "skill_name": skill_name,
            "old_version": old_version,
            "new_version": new_version,
            "success": success,
        },
    )


def record_update_check_metric(
    marketplace: str,
    skills_checked: int,
    updates_available: int,
) -> None:
    """Record update check metric.

    Args:
        marketplace: Marketplace checked
        skills_checked: Number of skills checked
        updates_available: Number of updates available
    """
    logger.info(
        "skill_update_check",
        extra={
            "marketplace": marketplace,
            "skills_checked": skills_checked,
            "updates_available": updates_available,
        },
    )


# =============================================================================
# Auto-Update Scheduler
# =============================================================================


class AutoUpdateScheduler:
    """Scheduler for automatic skill updates from marketplaces.

    Features:
    - Periodic checks for skill updates
    - Respects marketplace auto_sync configuration
    - Optional auto-apply of updates
    - Version tracking and notifications

    Attributes:
        update_interval_hours: Hours between update checks
        auto_apply: Whether to automatically apply updates
    """

    def __init__(
        self,
        update_interval_hours: int = 24,
        auto_apply: bool = False,
        registry: MarketplaceRegistry | None = None,
    ) -> None:
        """Initialize the auto-update scheduler.

        Args:
            update_interval_hours: Hours between update checks (default: 24)
            auto_apply: Automatically apply updates (default: False)
            registry: Marketplace registry (default: create new)
        """
        self.update_interval_hours = update_interval_hours
        self.auto_apply = auto_apply
        self._registry = registry or MarketplaceRegistry()
        self._installed_versions: dict[str, SkillVersion] = {}
        self._running = False
        self._task: asyncio.Task[None] | None = None

    def get_auto_sync_marketplaces(self) -> list[MarketplaceConfig]:
        """Get list of marketplaces with auto_sync enabled.

        Returns:
            List of marketplace configs with auto_sync=True
        """
        return [mp for mp in self._registry.list_all() if mp.auto_sync]

    async def check_updates_available(self) -> list[SkillUpdate]:
        """Check for available skill updates from all auto-sync marketplaces.

        Returns:
            List of available skill updates
        """
        updates: list[SkillUpdate] = []
        marketplaces = self.get_auto_sync_marketplaces()

        for marketplace in marketplaces:
            try:
                mp_updates = await self._check_marketplace_updates(marketplace)
                updates.extend(mp_updates)

                record_update_check_metric(
                    marketplace=marketplace.name,
                    skills_checked=len(self._installed_versions),
                    updates_available=len(mp_updates),
                )
            except Exception as e:
                logger.exception(f"Error checking updates from {marketplace.name}: {e}")

        return updates

    async def _check_marketplace_updates(self, marketplace: MarketplaceConfig) -> list[SkillUpdate]:
        """Check for updates from a specific marketplace.

        Args:
            marketplace: Marketplace to check

        Returns:
            List of available updates from this marketplace
        """
        updates: list[SkillUpdate] = []

        # Fetch available skills from marketplace
        try:
            from mcp_server_langgraph.skills.installer import SkillInstaller

            installer = SkillInstaller()
            available_skills = await installer.list_marketplace_skills(marketplace.name)

            for skill_info in available_skills:
                skill_name = skill_info.get("name", "")
                available_version = skill_info.get("version", "0.0.0")

                # Check if we have this skill installed
                if skill_name in self._installed_versions:
                    installed = self._installed_versions[skill_name]
                    if compare_versions(installed.version, available_version) < 0:
                        updates.append(
                            SkillUpdate(
                                skill_name=skill_name,
                                current_version=installed.version,
                                new_version=available_version,
                                marketplace=marketplace.name,
                                changelog=skill_info.get("changelog"),
                            )
                        )
        except Exception as e:
            logger.warning(f"Failed to check marketplace {marketplace.name}: {e}")

        return updates

    async def apply_updates(self) -> list[dict[str, Any]]:
        """Apply all available updates.

        Returns:
            List of update results
        """
        updates = await self.check_updates_available()
        results: list[dict[str, Any]] = []

        for update in updates:
            try:
                await self._apply_skill_update(update.skill_name, update.new_version)
                record_skill_update_metric(
                    skill_name=update.skill_name,
                    old_version=update.current_version,
                    new_version=update.new_version,
                    success=True,
                )
                results.append(
                    {
                        "skill_name": update.skill_name,
                        "success": True,
                        "new_version": update.new_version,
                    }
                )
            except Exception as e:
                logger.exception(f"Failed to apply update for {update.skill_name}: {e}")
                record_skill_update_metric(
                    skill_name=update.skill_name,
                    old_version=update.current_version,
                    new_version=update.new_version,
                    success=False,
                )
                results.append(
                    {
                        "skill_name": update.skill_name,
                        "success": False,
                        "error": str(e),
                    }
                )

        return results

    async def _apply_skill_update(self, skill_name: str, new_version: str) -> None:
        """Apply a single skill update.

        Args:
            skill_name: Name of skill to update
            new_version: Version to update to
        """
        from mcp_server_langgraph.skills.installer import SkillInstaller

        installer = SkillInstaller()
        await installer.install_skill(skill_name, version=new_version)

        # Update installed version tracking
        self._installed_versions[skill_name] = SkillVersion(
            skill_name=skill_name,
            version=new_version,
            marketplace=self._installed_versions.get(
                skill_name,
                SkillVersion(
                    skill_name=skill_name,
                    version="0.0.0",
                    marketplace="unknown",
                    installed_at=datetime.now(UTC),
                ),
            ).marketplace,
            installed_at=datetime.now(UTC),
        )

    async def _on_update_found(self, skill_name: str, current_version: str, new_version: str) -> None:
        """Handle when an update is found.

        Args:
            skill_name: Skill with available update
            current_version: Currently installed version
            new_version: Available new version
        """
        logger.info(f"Update available for {skill_name}: {current_version} -> {new_version}")

        await self._notify_update_available(skill_name, current_version, new_version)

        if self.auto_apply:
            await self._apply_skill_update(skill_name, new_version)

    async def _notify_update_available(self, skill_name: str, current_version: str, new_version: str) -> None:
        """Send notification about available update.

        Args:
            skill_name: Skill with available update
            current_version: Currently installed version
            new_version: Available new version
        """
        # This could integrate with the notification system
        logger.info(
            "skill_update_available",
            extra={
                "skill_name": skill_name,
                "current_version": current_version,
                "new_version": new_version,
            },
        )

    async def start(self) -> None:
        """Start the auto-update scheduler."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info(f"Auto-update scheduler started (interval: {self.update_interval_hours}h)")

    async def stop(self) -> None:
        """Stop the auto-update scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Auto-update scheduler stopped")

    async def _run_scheduler(self) -> None:
        """Run the scheduler loop."""
        while self._running:
            try:
                updates = await self.check_updates_available()

                for update in updates:
                    await self._on_update_found(
                        update.skill_name,
                        update.current_version,
                        update.new_version,
                    )

            except Exception as e:
                logger.exception(f"Error in auto-update scheduler: {e}")

            # Wait for next check interval
            await asyncio.sleep(self.update_interval_hours * 3600)

    def register_installed_skill(self, skill_name: str, version: str, marketplace: str) -> None:
        """Register an installed skill for version tracking.

        Args:
            skill_name: Name of the skill
            version: Installed version
            marketplace: Source marketplace
        """
        self._installed_versions[skill_name] = SkillVersion(
            skill_name=skill_name,
            version=version,
            marketplace=marketplace,
            installed_at=datetime.now(UTC),
        )


# =============================================================================
# Singleton & Lifecycle Management
# =============================================================================

_auto_update_scheduler: AutoUpdateScheduler | None = None


def get_feature_flags() -> Any:
    """Get feature flags (lazy import to avoid circular deps)."""
    from mcp_server_langgraph.core.feature_flags import get_feature_flags as _get_ff

    return _get_ff()


def is_auto_update_enabled() -> bool:
    """Check if auto-update is enabled via feature flag.

    Returns:
        True if SKILLS_MARKETPLACE feature flag is enabled
    """
    flags = get_feature_flags()
    return getattr(flags, "enable_skills_marketplace", False)


def get_auto_update_scheduler() -> AutoUpdateScheduler:
    """Get the singleton auto-update scheduler.

    Returns:
        The global AutoUpdateScheduler instance
    """
    global _auto_update_scheduler
    if _auto_update_scheduler is None:
        _auto_update_scheduler = AutoUpdateScheduler()
    return _auto_update_scheduler


def reset_auto_update_scheduler() -> None:
    """Reset the singleton scheduler (for testing)."""
    global _auto_update_scheduler
    _auto_update_scheduler = None


async def initialize_auto_update_scheduler(
    update_interval_hours: int = 24,
    auto_apply: bool = False,
) -> AutoUpdateScheduler | None:
    """Initialize and start the auto-update scheduler.

    Args:
        update_interval_hours: Hours between update checks
        auto_apply: Whether to auto-apply updates

    Returns:
        The initialized scheduler, or None if disabled
    """
    global _auto_update_scheduler

    if not is_auto_update_enabled():
        logger.info("Skills marketplace auto-update disabled by feature flag")
        return None

    _auto_update_scheduler = AutoUpdateScheduler(
        update_interval_hours=update_interval_hours,
        auto_apply=auto_apply,
    )
    await _auto_update_scheduler.start()
    logger.info(f"Auto-update scheduler started (interval: {update_interval_hours}h)")
    return _auto_update_scheduler


async def shutdown_auto_update_scheduler() -> None:
    """Shutdown the auto-update scheduler."""
    global _auto_update_scheduler
    if _auto_update_scheduler is not None:
        await _auto_update_scheduler.stop()
        logger.info("Auto-update scheduler stopped")
