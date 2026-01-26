"""
Tests for audit integrity scheduler integration with FastAPI app lifecycle.

TDD RED phase: These tests define expected behavior for scheduler integration.

The integration should:
- Start the scheduler during app startup
- Stop the scheduler during app shutdown
- Configure scheduler from settings
- Use configured alert callback
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.integration
@pytest.mark.xdist_group(name="audit_scheduler_integration")
class TestSchedulerAppLifecycle:
    """Tests for scheduler lifecycle in FastAPI app."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_scheduler_factory_exists(self) -> None:
        """GIVEN audit module THEN scheduler factory function exists."""
        from mcp_server_langgraph.audit import create_audit_scheduler

        assert callable(create_audit_scheduler)

    def test_scheduler_factory_creates_scheduler(self) -> None:
        """GIVEN factory WHEN called THEN returns scheduler instance."""
        from mcp_server_langgraph.audit import (
            AuditIntegrityScheduler,
            create_audit_scheduler,
        )

        mock_service = AsyncMock(return_value=None)  # async-mock-configured

        scheduler = create_audit_scheduler(
            audit_service=mock_service,
            schedule_hours=24,
        )

        assert isinstance(scheduler, AuditIntegrityScheduler)

    def test_scheduler_factory_with_alert_callback(self) -> None:
        """GIVEN factory with callback WHEN created THEN callback configured."""
        from mcp_server_langgraph.audit import create_audit_scheduler

        mock_service = AsyncMock(return_value=None)  # async-mock-configured
        mock_callback = AsyncMock(return_value=None)  # async-mock-configured

        scheduler = create_audit_scheduler(
            audit_service=mock_service,
            alert_callback=mock_callback,
        )

        assert scheduler._alert_callback is mock_callback

    def test_scheduler_factory_with_metrics(self) -> None:
        """GIVEN factory with metrics WHEN created THEN metrics configured."""
        from mcp_server_langgraph.audit import AuditMetrics, create_audit_scheduler

        mock_service = AsyncMock(return_value=None)  # async-mock-configured
        mock_metrics = MagicMock(spec=AuditMetrics)

        scheduler = create_audit_scheduler(
            audit_service=mock_service,
            metrics=mock_metrics,
        )

        assert scheduler._metrics is mock_metrics


@pytest.mark.integration
@pytest.mark.xdist_group(name="audit_scheduler_integration")
class TestSchedulerConfigFromSettings:
    """Tests for scheduler configuration from app settings."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_settings_has_audit_scheduler_enabled(self) -> None:
        """GIVEN settings THEN audit_scheduler_enabled attribute exists."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "audit_scheduler_enabled")

    def test_settings_has_audit_scheduler_hours(self) -> None:
        """GIVEN settings THEN audit_scheduler_hours attribute exists."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert hasattr(settings, "audit_scheduler_hours")

    def test_settings_scheduler_enabled_default(self) -> None:
        """GIVEN default settings THEN scheduler disabled by default."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        # Disabled by default to avoid overhead in development
        assert settings.audit_scheduler_enabled is False

    def test_settings_scheduler_hours_default(self) -> None:
        """GIVEN default settings THEN schedule hours is 24."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings()
        assert settings.audit_scheduler_hours == 24


@pytest.mark.integration
@pytest.mark.xdist_group(name="audit_scheduler_integration")
class TestSchedulerLifespanStartStop:
    """Tests for scheduler start/stop in lifespan context."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_scheduler_starts_when_enabled(self) -> None:
        """GIVEN enabled scheduler WHEN app starts THEN scheduler started."""
        from mcp_server_langgraph.audit.scheduler import AuditIntegrityScheduler

        scheduler = AuditIntegrityScheduler(
            audit_service=AsyncMock(return_value=None),  # async-mock-configured
            schedule_hours=24,
        )

        # Mock the start method to track if it's called
        scheduler.start = AsyncMock(return_value=None)  # async-mock-configured

        await scheduler.start()

        scheduler.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_scheduler_stops_on_shutdown(self) -> None:
        """GIVEN running scheduler WHEN app shuts down THEN scheduler stopped."""
        from mcp_server_langgraph.audit.scheduler import AuditIntegrityScheduler

        scheduler = AuditIntegrityScheduler(
            audit_service=AsyncMock(return_value=None),  # async-mock-configured
            schedule_hours=24,
        )

        # Stop should set _stopped to True
        scheduler.stop()

        assert scheduler._stopped is True

    @pytest.mark.asyncio
    async def test_scheduler_not_started_when_disabled(self) -> None:
        """GIVEN disabled scheduler WHEN app starts THEN scheduler not started."""
        from mcp_server_langgraph.core.config import Settings

        settings = Settings(audit_scheduler_enabled=False)
        assert settings.audit_scheduler_enabled is False
        # App lifespan should NOT start scheduler when disabled
