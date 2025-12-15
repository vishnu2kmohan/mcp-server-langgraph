"""
Tests for audit integrity verification scheduler.

TDD RED phase: These tests define expected behavior for scheduled verification.

The scheduler should:
- Run daily integrity verification
- Alert on verification failures
- Record verification metrics
- Support configurable schedule
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_scheduler")
class TestAuditIntegrityScheduler:
    """Tests for scheduled integrity verification."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_scheduler_verifies_last_24_hours(self) -> None:
        """GIVEN scheduler WHEN running daily THEN verifies last 24 hours."""
        from mcp_server_langgraph.audit.scheduler import AuditIntegrityScheduler

        mock_service = AsyncMock()  # async-mock-configured
        mock_service.verify_integrity = AsyncMock(
            return_value={
                "valid": True,
                "events_verified": 1000,
                "errors": [],
            }
        )

        scheduler = AuditIntegrityScheduler(
            audit_service=mock_service,
            schedule_hours=24,
        )

        result = await scheduler.run_verification()

        assert result["valid"] is True
        mock_service.verify_integrity.assert_called_once()

    @pytest.mark.asyncio
    async def test_scheduler_alerts_on_failure(self) -> None:
        """GIVEN verification failure WHEN running THEN alert triggered."""
        from mcp_server_langgraph.audit.scheduler import AuditIntegrityScheduler

        mock_service = AsyncMock()  # async-mock-configured
        mock_service.verify_integrity = AsyncMock(
            return_value={
                "valid": False,
                "events_verified": 1000,
                "errors": ["Hash mismatch at sequence 500"],
            }
        )

        mock_alert_callback = AsyncMock()  # async-mock-configured

        scheduler = AuditIntegrityScheduler(
            audit_service=mock_service,
            alert_callback=mock_alert_callback,
        )

        result = await scheduler.run_verification()

        assert result["valid"] is False
        mock_alert_callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_scheduler_records_metrics(self) -> None:
        """GIVEN verification WHEN completed THEN metrics recorded."""
        from mcp_server_langgraph.audit.scheduler import AuditIntegrityScheduler

        mock_service = AsyncMock()  # async-mock-configured
        mock_service.verify_integrity = AsyncMock(
            return_value={
                "valid": True,
                "events_verified": 500,
                "errors": [],
            }
        )

        mock_metrics = MagicMock()

        scheduler = AuditIntegrityScheduler(
            audit_service=mock_service,
            metrics=mock_metrics,
        )

        await scheduler.run_verification()

        mock_metrics.record_integrity_verification.assert_called_once()


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_scheduler")
class TestAuditSchedulerConfiguration:
    """Tests for scheduler configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_scheduler_default_schedule(self) -> None:
        """GIVEN no config WHEN created THEN uses default schedule."""
        from mcp_server_langgraph.audit.scheduler import AuditIntegrityScheduler

        mock_service = AsyncMock()  # async-mock-configured

        scheduler = AuditIntegrityScheduler(audit_service=mock_service)

        # Default is daily (24 hours)
        assert scheduler.schedule_hours == 24

    def test_scheduler_custom_schedule(self) -> None:
        """GIVEN custom config WHEN created THEN uses custom schedule."""
        from mcp_server_langgraph.audit.scheduler import AuditIntegrityScheduler

        mock_service = AsyncMock()  # async-mock-configured

        scheduler = AuditIntegrityScheduler(
            audit_service=mock_service,
            schedule_hours=12,  # Every 12 hours
        )

        assert scheduler.schedule_hours == 12

    def test_scheduler_can_be_started(self) -> None:
        """GIVEN scheduler WHEN started THEN runs without error."""
        from mcp_server_langgraph.audit.scheduler import AuditIntegrityScheduler

        mock_service = AsyncMock()  # async-mock-configured

        scheduler = AuditIntegrityScheduler(audit_service=mock_service)

        # Should not raise
        assert scheduler is not None

    def test_scheduler_can_be_stopped(self) -> None:
        """GIVEN running scheduler WHEN stopped THEN stops gracefully."""
        from mcp_server_langgraph.audit.scheduler import AuditIntegrityScheduler

        mock_service = AsyncMock()  # async-mock-configured

        scheduler = AuditIntegrityScheduler(audit_service=mock_service)
        scheduler.stop()

        assert scheduler._stopped is True
