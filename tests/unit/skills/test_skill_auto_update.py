"""
Tests for Skills Auto-Update from Marketplace.

TDD tests for automatic skill synchronization with marketplaces.
"""

from __future__ import annotations

import gc
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest


pytestmark = [pytest.mark.unit, pytest.mark.skills, pytest.mark.skills_marketplace]


@pytest.mark.xdist_group(name="skills_auto_update")
class TestSkillsAutoUpdateScheduler:
    """Tests for skills auto-update scheduler."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_auto_update_scheduler_exists(self) -> None:
        """Test that AutoUpdateScheduler class exists."""
        from mcp_server_langgraph.skills.auto_update import AutoUpdateScheduler

        assert AutoUpdateScheduler is not None

    def test_scheduler_initialization_with_custom_interval(self) -> None:
        """Test scheduler can be initialized with update interval."""
        from mcp_server_langgraph.skills.auto_update import AutoUpdateScheduler

        scheduler = AutoUpdateScheduler(update_interval_hours=24)
        assert scheduler is not None
        assert scheduler.update_interval_hours == 24

    def test_scheduler_default_interval(self) -> None:
        """Test scheduler has sensible default interval (24 hours)."""
        from mcp_server_langgraph.skills.auto_update import AutoUpdateScheduler

        scheduler = AutoUpdateScheduler()
        assert scheduler.update_interval_hours == 24

    @pytest.mark.asyncio
    async def test_scheduler_check_updates_available(self) -> None:
        """Test scheduler can check for available updates."""
        from mcp_server_langgraph.skills.auto_update import AutoUpdateScheduler

        scheduler = AutoUpdateScheduler()
        updates = await scheduler.check_updates_available()
        assert isinstance(updates, list)

    @pytest.mark.asyncio
    async def test_scheduler_apply_updates(self) -> None:
        """Test scheduler can apply available updates."""
        from mcp_server_langgraph.skills.auto_update import AutoUpdateScheduler, SkillUpdate

        scheduler = AutoUpdateScheduler()
        with patch.object(scheduler, "check_updates_available", new_callable=AsyncMock) as mock_check:
            # Use SkillUpdate objects, not dicts
            mock_check.return_value = [
                SkillUpdate(skill_name="web-research", current_version="1.0.0", new_version="1.1.0", marketplace="anthropic")
            ]

            # Also mock the apply method since we don't have real installer
            with patch.object(scheduler, "_apply_skill_update", new_callable=AsyncMock):
                result = await scheduler.apply_updates()
                assert result is not None
                assert len(result) == 1
                assert result[0]["skill_name"] == "web-research"
                assert result[0]["success"] is True

    @pytest.mark.asyncio
    async def test_scheduler_respects_auto_sync_flag(self) -> None:
        """Test scheduler only updates skills from marketplaces with auto_sync=True."""
        from mcp_server_langgraph.skills.auto_update import AutoUpdateScheduler

        scheduler = AutoUpdateScheduler()

        # Verify scheduler only returns marketplaces with auto_sync=True
        marketplaces = scheduler.get_auto_sync_marketplaces()
        # Should only include marketplaces with auto_sync=True
        for mp in marketplaces:
            assert mp.auto_sync is True


@pytest.mark.xdist_group(name="skills_version_tracking")
class TestSkillVersionTracking:
    """Tests for skill version tracking."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_skill_version_model_exists(self) -> None:
        """Test that SkillVersion model exists."""
        from mcp_server_langgraph.skills.auto_update import SkillVersion

        assert SkillVersion is not None

    def test_skill_version_has_required_fields(self) -> None:
        """Test SkillVersion has required fields."""
        from mcp_server_langgraph.skills.auto_update import SkillVersion

        version = SkillVersion(
            skill_name="web-research",
            version="1.0.0",
            marketplace="anthropic",
            installed_at=datetime.utcnow(),
        )

        assert version.skill_name == "web-research"
        assert version.version == "1.0.0"
        assert version.marketplace == "anthropic"
        assert version.installed_at is not None

    def test_skill_version_comparison(self) -> None:
        """Test comparing skill versions."""
        from mcp_server_langgraph.skills.auto_update import compare_versions

        assert compare_versions("1.0.0", "1.0.1") < 0
        assert compare_versions("1.1.0", "1.0.0") > 0
        assert compare_versions("1.0.0", "1.0.0") == 0
        assert compare_versions("2.0.0", "1.9.9") > 0


@pytest.mark.xdist_group(name="skills_update_notifications")
class TestSkillUpdateNotifications:
    """Tests for skill update notifications."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_update_notification_sent_on_new_version(self) -> None:
        """Test notification is sent when new version is available."""
        from mcp_server_langgraph.skills.auto_update import AutoUpdateScheduler

        scheduler = AutoUpdateScheduler()
        with patch.object(scheduler, "_notify_update_available", new_callable=AsyncMock) as mock_notify:
            await scheduler._on_update_found("web-research", "1.0.0", "1.1.0")
            mock_notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_applies_when_auto_apply_enabled(self) -> None:
        """Test update is applied automatically when auto_apply is enabled."""
        from mcp_server_langgraph.skills.auto_update import AutoUpdateScheduler

        scheduler = AutoUpdateScheduler(auto_apply=True)

        with patch.object(scheduler, "_apply_skill_update", new_callable=AsyncMock) as mock_apply:
            await scheduler._on_update_found("web-research", "1.0.0", "1.1.0")
            mock_apply.assert_called_once_with("web-research", "1.1.0")


@pytest.mark.xdist_group(name="skills_update_metrics")
class TestSkillUpdateMetrics:
    """Tests for skill update metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_update_metrics_recorded(self) -> None:
        """Test that skill update metrics are recorded."""
        from mcp_server_langgraph.skills.auto_update import record_skill_update_metric

        # Should not raise
        record_skill_update_metric(
            skill_name="web-research",
            old_version="1.0.0",
            new_version="1.1.0",
            success=True,
        )

    def test_update_check_metrics_recorded(self) -> None:
        """Test that update check metrics are recorded."""
        from mcp_server_langgraph.skills.auto_update import record_update_check_metric

        # Should not raise
        record_update_check_metric(
            marketplace="anthropic",
            skills_checked=10,
            updates_available=2,
        )
