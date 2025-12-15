"""
Tests for audit scheduler integration with FastAPI app lifespan.

TDD RED phase: These tests define expected behavior for scheduler integration.

The integration should:
- Start the audit scheduler on app startup when enabled
- Not start the scheduler when disabled
- Stop the scheduler gracefully on app shutdown
- Use configuration from settings
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from mcp_server_langgraph.core.config import Settings

pytestmark = pytest.mark.integration


@pytest.mark.integration
@pytest.mark.xdist_group(name="audit_lifespan")
class TestAuditSchedulerLifespanIntegration:
    """Tests for audit scheduler lifecycle in FastAPI app."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_scheduler_starts_when_enabled(self) -> None:
        """
        GIVEN audit_scheduler_enabled=True in settings
        WHEN the app starts
        THEN the audit scheduler is started.
        """
        from mcp_server_langgraph.app import create_app

        # Create settings with scheduler enabled
        test_settings = Settings(
            audit_scheduler_enabled=True,
            audit_scheduler_hours=1,
            environment="test",
        )

        # Mock the scheduler factory and audit service
        mock_scheduler = MagicMock()
        mock_scheduler.start = AsyncMock()  # noqa: async-mock-config - async method (awaited in app.py)
        mock_scheduler.stop = MagicMock()  # sync method (not awaited in app.py)

        with (
            patch(
                "mcp_server_langgraph.app.create_audit_scheduler",
                return_value=mock_scheduler,
            ),
            patch(
                "mcp_server_langgraph.app.get_audit_service",
                return_value=MagicMock(),
            ),
        ):
            # Create app with test settings
            app = create_app(
                settings_override=test_settings,
                skip_startup_validation=True,
            )

            # Use TestClient to trigger lifespan
            with TestClient(app):
                # Scheduler should have been started
                mock_scheduler.start.assert_called_once()

            # Scheduler should have been stopped on shutdown
            mock_scheduler.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_scheduler_not_started_when_disabled(self) -> None:
        """
        GIVEN audit_scheduler_enabled=False in settings
        WHEN the app starts
        THEN the audit scheduler is NOT started.
        """
        from mcp_server_langgraph.app import create_app

        # Create settings with scheduler disabled
        test_settings = Settings(
            audit_scheduler_enabled=False,
            environment="test",
        )

        # Mock the scheduler factory
        with patch("mcp_server_langgraph.app.create_audit_scheduler") as mock_create_scheduler:
            # Create app with test settings
            app = create_app(
                settings_override=test_settings,
                skip_startup_validation=True,
            )

            # Use TestClient to trigger lifespan
            with TestClient(app):
                pass

            # Scheduler factory should NOT have been called
            mock_create_scheduler.assert_not_called()

    @pytest.mark.asyncio
    async def test_scheduler_uses_config_hours(self) -> None:
        """
        GIVEN custom audit_scheduler_hours in settings
        WHEN the scheduler is created
        THEN it uses the configured hours.
        """
        from mcp_server_langgraph.app import create_app

        # Create settings with custom hours
        test_settings = Settings(
            audit_scheduler_enabled=True,
            audit_scheduler_hours=12,  # Custom interval
            environment="test",
        )

        mock_scheduler = MagicMock()
        mock_scheduler.start = AsyncMock()  # noqa: async-mock-config - async method (awaited in app.py)
        mock_scheduler.stop = MagicMock()  # sync method (not awaited in app.py)

        with (
            patch(
                "mcp_server_langgraph.app.create_audit_scheduler",
                return_value=mock_scheduler,
            ) as mock_create_scheduler,
            patch(
                "mcp_server_langgraph.app.get_audit_service",
                return_value=MagicMock(),
            ),
        ):
            app = create_app(
                settings_override=test_settings,
                skip_startup_validation=True,
            )

            with TestClient(app):
                pass

            # Verify scheduler was created with correct hours
            mock_create_scheduler.assert_called_once()
            call_kwargs = mock_create_scheduler.call_args[1]
            assert call_kwargs["schedule_hours"] == 12

    @pytest.mark.asyncio
    async def test_scheduler_stops_gracefully_on_error(self) -> None:
        """
        GIVEN the scheduler is running
        WHEN an error occurs during shutdown
        THEN the error is logged but doesn't crash the app.
        """
        from mcp_server_langgraph.app import create_app

        test_settings = Settings(
            audit_scheduler_enabled=True,
            audit_scheduler_hours=1,
            environment="test",
        )

        mock_scheduler = MagicMock()
        mock_scheduler.start = AsyncMock()  # noqa: async-mock-config - async method (awaited in app.py)
        # Simulate error on stop (sync method, not awaited in app.py)
        mock_scheduler.stop = MagicMock(side_effect=Exception("Shutdown error"))

        with (
            patch(
                "mcp_server_langgraph.app.create_audit_scheduler",
                return_value=mock_scheduler,
            ),
            patch(
                "mcp_server_langgraph.app.get_audit_service",
                return_value=MagicMock(),
            ),
        ):
            app = create_app(
                settings_override=test_settings,
                skip_startup_validation=True,
            )

            # Should not raise even if stop() fails
            with TestClient(app):
                pass

            # Stop was attempted
            mock_scheduler.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_scheduler_not_started_without_audit_service(self) -> None:
        """
        GIVEN audit_scheduler_enabled=True but no audit service configured
        WHEN the app starts
        THEN the scheduler is NOT started (graceful degradation).
        """
        from mcp_server_langgraph.app import create_app

        test_settings = Settings(
            audit_scheduler_enabled=True,
            audit_scheduler_hours=1,
            environment="test",
        )

        with (
            patch("mcp_server_langgraph.app.create_audit_scheduler") as mock_create_scheduler,
            patch(
                "mcp_server_langgraph.app.get_audit_service",
                return_value=None,  # No audit service
            ),
        ):
            app = create_app(
                settings_override=test_settings,
                skip_startup_validation=True,
            )

            with TestClient(app):
                pass

            # Scheduler should NOT have been created without audit service
            mock_create_scheduler.assert_not_called()


@pytest.mark.integration
@pytest.mark.xdist_group(name="audit_lifespan")
class TestAuditSchedulerDependencies:
    """Tests for audit scheduler dependency injection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_scheduler_receives_audit_service(self) -> None:
        """
        GIVEN the app creates an audit scheduler
        WHEN the scheduler is initialized
        THEN it receives the audit service instance.
        """
        from mcp_server_langgraph.app import create_app

        test_settings = Settings(
            audit_scheduler_enabled=True,
            audit_scheduler_hours=24,
            environment="test",
        )

        mock_scheduler = MagicMock()
        mock_scheduler.start = AsyncMock()  # noqa: async-mock-config - async method (awaited in app.py)
        mock_scheduler.stop = MagicMock()  # sync method (not awaited in app.py)
        mock_audit_service = MagicMock()

        with (
            patch(
                "mcp_server_langgraph.app.create_audit_scheduler",
                return_value=mock_scheduler,
            ) as mock_create_scheduler,
            patch(
                "mcp_server_langgraph.app.get_audit_service",
                return_value=mock_audit_service,
            ),
        ):
            app = create_app(
                settings_override=test_settings,
                skip_startup_validation=True,
            )

            with TestClient(app):
                pass

            # Verify audit_service was passed
            call_kwargs = mock_create_scheduler.call_args[1]
            assert "audit_service" in call_kwargs
            assert call_kwargs["audit_service"] is mock_audit_service
