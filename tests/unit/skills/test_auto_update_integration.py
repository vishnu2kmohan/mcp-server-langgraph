"""
Tests for Skills Auto-Update App Lifecycle Integration.

TDD tests for wiring AutoUpdateScheduler to application startup/shutdown.
"""

from __future__ import annotations

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="skills_auto_update_lifecycle")
class TestAutoUpdateLifecycleIntegration:
    """Tests for auto-update scheduler lifecycle management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_get_auto_update_scheduler_returns_scheduler(self) -> None:
        """Test get_auto_update_scheduler returns a scheduler instance."""
        from mcp_server_langgraph.skills.auto_update import get_auto_update_scheduler

        scheduler = get_auto_update_scheduler()
        assert scheduler is not None

    def test_get_auto_update_scheduler_singleton(self) -> None:
        """Test scheduler is a singleton."""
        from mcp_server_langgraph.skills.auto_update import (
            get_auto_update_scheduler,
            reset_auto_update_scheduler,
        )

        # Reset to ensure clean state
        reset_auto_update_scheduler()

        scheduler1 = get_auto_update_scheduler()
        scheduler2 = get_auto_update_scheduler()
        assert scheduler1 is scheduler2

        # Cleanup
        reset_auto_update_scheduler()

    def test_scheduler_respects_feature_flag(self) -> None:
        """Test scheduler respects SKILLS_MARKETPLACE feature flag."""
        from mcp_server_langgraph.skills.auto_update import (
            is_auto_update_enabled,
        )

        # Should check feature flag
        with patch("mcp_server_langgraph.skills.auto_update.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_skills_marketplace=True)
            assert is_auto_update_enabled() is True

            mock_flags.return_value = MagicMock(enable_skills_marketplace=False)
            assert is_auto_update_enabled() is False

    @pytest.mark.asyncio
    async def test_initialize_auto_update_scheduler(self) -> None:
        """Test initialize_auto_update_scheduler starts the scheduler."""
        from mcp_server_langgraph.skills.auto_update import (
            initialize_auto_update_scheduler,
            reset_auto_update_scheduler,
        )

        reset_auto_update_scheduler()

        with patch("mcp_server_langgraph.skills.auto_update.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_skills_marketplace=True)

            scheduler = await initialize_auto_update_scheduler(
                update_interval_hours=24,
                auto_apply=False,
            )

            assert scheduler is not None
            # Scheduler should be started
            assert scheduler._running is True

            # Cleanup
            await scheduler.stop()
            reset_auto_update_scheduler()

    @pytest.mark.asyncio
    async def test_shutdown_auto_update_scheduler(self) -> None:
        """Test shutdown_auto_update_scheduler stops the scheduler."""
        from mcp_server_langgraph.skills.auto_update import (
            initialize_auto_update_scheduler,
            reset_auto_update_scheduler,
            shutdown_auto_update_scheduler,
        )

        reset_auto_update_scheduler()

        with patch("mcp_server_langgraph.skills.auto_update.get_feature_flags") as mock_flags:
            mock_flags.return_value = MagicMock(enable_skills_marketplace=True)

            scheduler = await initialize_auto_update_scheduler(
                update_interval_hours=24,
                auto_apply=False,
            )
            assert scheduler._running is True

            await shutdown_auto_update_scheduler()
            assert scheduler._running is False

            reset_auto_update_scheduler()


@pytest.mark.xdist_group(name="skills_auto_update_api")
class TestAutoUpdateAPIEndpoint:
    """Tests for auto-update API endpoint."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_skills_updates_endpoint_exists(self) -> None:
        """Test /api/v1/admin/skills/updates endpoint exists."""
        from mcp_server_langgraph.api.v1.skills import router

        # Find route in skills router
        route_paths = [route.path for route in router.routes]
        assert "/updates" in route_paths or any("updates" in path for path in route_paths)

    @pytest.mark.asyncio
    async def test_check_updates_returns_available_updates(self) -> None:
        """Test check updates returns list of available updates."""
        from mcp_server_langgraph.api.v1.skills import check_skill_updates
        from mcp_server_langgraph.skills.auto_update import AutoUpdateScheduler

        mock_user = {"user_id": "admin-test-user", "roles": ["admin"]}

        with patch("mcp_server_langgraph.api.v1.skills.get_auto_update_scheduler") as mock_get:
            mock_scheduler = AsyncMock(spec=AutoUpdateScheduler)
            mock_scheduler.check_updates_available = AsyncMock(return_value=[])
            mock_get.return_value = mock_scheduler

            result = await check_skill_updates(user=mock_user)
            assert result is not None
            assert "updates" in result

    @pytest.mark.asyncio
    async def test_apply_updates_applies_available_updates(self) -> None:
        """Test apply updates endpoint applies updates."""
        from mcp_server_langgraph.api.v1.skills import apply_skill_updates
        from mcp_server_langgraph.skills.auto_update import AutoUpdateScheduler

        mock_user = {"user_id": "admin-test-user", "roles": ["admin"]}

        with patch("mcp_server_langgraph.api.v1.skills.get_auto_update_scheduler") as mock_get:
            mock_scheduler = AsyncMock(spec=AutoUpdateScheduler)
            mock_scheduler.apply_updates = AsyncMock(return_value=[])
            mock_get.return_value = mock_scheduler

            result = await apply_skill_updates(user=mock_user)
            assert result is not None
            assert "applied" in result


@pytest.mark.xdist_group(name="skills_auto_update_settings")
class TestAutoUpdateSettings:
    """Tests for auto-update settings integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_settings_has_update_interval(self) -> None:
        """Test Settings has skill_update_interval_hours."""
        from mcp_server_langgraph.core.config._settings import Settings

        settings = Settings()
        assert hasattr(settings, "skill_update_interval_hours")

    def test_settings_has_auto_apply_flag(self) -> None:
        """Test Settings has skill_auto_apply_updates."""
        from mcp_server_langgraph.core.config._settings import Settings

        settings = Settings()
        assert hasattr(settings, "skill_auto_apply_updates")

    def test_default_update_interval_is_24_hours(self) -> None:
        """Test default update interval is 24 hours."""
        from mcp_server_langgraph.core.config._settings import Settings

        settings = Settings()
        assert settings.skill_update_interval_hours == 24

    def test_default_auto_apply_is_false(self) -> None:
        """Test default auto_apply is False (requires admin approval)."""
        from mcp_server_langgraph.core.config._settings import Settings

        settings = Settings()
        assert settings.skill_auto_apply_updates is False
