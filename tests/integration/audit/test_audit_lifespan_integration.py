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
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from mcp_server_langgraph.core.config import Settings

pytestmark = pytest.mark.integration


@pytest.mark.integration
@pytest.mark.xdist_group(name="audit_lifespan")
class TestAuditSchedulerLifespanIntegration:
    """Tests for audit scheduler lifecycle in FastAPI app."""

    def setup_method(self) -> None:
        """Reset singleton dependencies to prevent xdist pollution.

        PYTEST-XDIST FIX (2025-12-16): In parallel execution, other tests may
        pollute singleton state. Reset before each test to ensure clean state.
        """
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    @pytest.mark.asyncio
    async def test_scheduler_starts_when_enabled(self) -> None:
        """
        GIVEN audit_scheduler_enabled=True in settings
        WHEN the app starts
        THEN the audit scheduler is started.

        PYTEST-XDIST FIX (2025-12-16): Use side_effect with factory function
        instead of return_value to prevent MagicMock pollution across xdist workers.
        """
        from mcp_server_langgraph.app import create_app

        # Create settings with scheduler enabled
        test_settings = Settings(
            audit_scheduler_enabled=True,
            audit_scheduler_hours=1,
            environment="test",
        )

        # PYTEST-XDIST FIX (2025-12-16): Track calls via mutable container instead
        # of relying on MagicMock's call tracking which can be polluted
        call_tracker = {"start_called": False, "stop_called": False}

        def create_mock_scheduler(**kwargs):
            """Factory function to create fresh mock scheduler for each call."""
            mock = MagicMock()

            async def mock_start():
                call_tracker["start_called"] = True

            def mock_stop():
                call_tracker["stop_called"] = True

            mock.start = mock_start
            mock.stop = mock_stop
            return mock

        with (
            patch(
                "mcp_server_langgraph.app.create_audit_scheduler",
                side_effect=create_mock_scheduler,
            ),
            patch(
                "mcp_server_langgraph.app.get_audit_service",
                side_effect=lambda: MagicMock(),
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
                assert call_tracker["start_called"], "Expected scheduler.start() to be called"

            # Scheduler should have been stopped on shutdown
            assert call_tracker["stop_called"], "Expected scheduler.stop() to be called"

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

        PYTEST-XDIST FIX (2025-12-16): Use side_effect with factory function
        instead of return_value to prevent MagicMock pollution across xdist workers.
        """
        from mcp_server_langgraph.app import create_app

        # Create settings with custom hours
        test_settings = Settings(
            audit_scheduler_enabled=True,
            audit_scheduler_hours=12,  # Custom interval
            environment="test",
        )

        # PYTEST-XDIST FIX: Track call kwargs via mutable container
        call_tracker = {"create_kwargs": None}

        def create_mock_scheduler(**kwargs):
            """Factory function to create fresh mock scheduler for each call."""
            call_tracker["create_kwargs"] = kwargs
            mock = MagicMock()

            async def mock_start():
                pass

            def mock_stop():
                pass

            mock.start = mock_start
            mock.stop = mock_stop
            return mock

        with (
            patch(
                "mcp_server_langgraph.app.create_audit_scheduler",
                side_effect=create_mock_scheduler,
            ),
            patch(
                "mcp_server_langgraph.app.get_audit_service",
                side_effect=lambda: MagicMock(),
            ),
        ):
            app = create_app(
                settings_override=test_settings,
                skip_startup_validation=True,
            )

            with TestClient(app):
                pass

            # Verify scheduler was created with correct hours
            assert call_tracker["create_kwargs"] is not None, "create_audit_scheduler should have been called"
            assert call_tracker["create_kwargs"]["schedule_hours"] == 12

    @pytest.mark.asyncio
    async def test_scheduler_stops_gracefully_on_error(self) -> None:
        """
        GIVEN the scheduler is running
        WHEN an error occurs during shutdown
        THEN the error is logged but doesn't crash the app.

        PYTEST-XDIST FIX (2025-12-16): Use side_effect with factory function
        instead of return_value to prevent MagicMock pollution across xdist workers.
        """
        from mcp_server_langgraph.app import create_app

        test_settings = Settings(
            audit_scheduler_enabled=True,
            audit_scheduler_hours=1,
            environment="test",
        )

        # PYTEST-XDIST FIX: Track calls via mutable container
        call_tracker = {"stop_called": False}

        def create_mock_scheduler(**kwargs):
            """Factory function to create fresh mock scheduler for each call."""
            mock = MagicMock()

            async def mock_start():
                pass

            def mock_stop():
                call_tracker["stop_called"] = True
                raise Exception("Shutdown error")

            mock.start = mock_start
            mock.stop = mock_stop
            return mock

        with (
            patch(
                "mcp_server_langgraph.app.create_audit_scheduler",
                side_effect=create_mock_scheduler,
            ),
            patch(
                "mcp_server_langgraph.app.get_audit_service",
                side_effect=lambda: MagicMock(),
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
            assert call_tracker["stop_called"], "Expected scheduler.stop() to be called"

    @pytest.mark.asyncio
    async def test_scheduler_not_started_without_audit_service(self) -> None:
        """
        GIVEN audit_scheduler_enabled=True but no audit service configured
        WHEN the app starts
        THEN the scheduler is NOT started (graceful degradation).

        PYTEST-XDIST FIX (2025-12-16): Use side_effect with lambda instead of
        return_value=None to prevent MagicMock pollution across xdist workers.
        """
        from mcp_server_langgraph.app import create_app

        test_settings = Settings(
            audit_scheduler_enabled=True,
            audit_scheduler_hours=1,
            environment="test",
        )

        # PYTEST-XDIST FIX: Track calls via mutable container
        call_tracker = {"scheduler_created": False}

        def mock_create_scheduler_tracking(**kwargs):
            """Track if create_audit_scheduler was called."""
            call_tracker["scheduler_created"] = True
            return MagicMock()

        with (
            patch(
                "mcp_server_langgraph.app.create_audit_scheduler",
                side_effect=mock_create_scheduler_tracking,
            ),
            patch(
                "mcp_server_langgraph.app.get_audit_service",
                side_effect=lambda: None,  # No audit service - use side_effect for xdist safety
            ),
        ):
            app = create_app(
                settings_override=test_settings,
                skip_startup_validation=True,
            )

            with TestClient(app):
                pass

            # Scheduler should NOT have been created without audit service
            assert not call_tracker["scheduler_created"], "Expected scheduler to NOT be created when audit service is None"


@pytest.mark.integration
@pytest.mark.xdist_group(name="audit_lifespan")
class TestAuditSchedulerDependencies:
    """Tests for audit scheduler dependency injection."""

    def setup_method(self) -> None:
        """Reset singleton dependencies to prevent xdist pollution."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        from mcp_server_langgraph.core.dependencies import reset_singleton_dependencies

        reset_singleton_dependencies()
        gc.collect()

    @pytest.mark.asyncio
    async def test_scheduler_receives_audit_service(self) -> None:
        """
        GIVEN the app creates an audit scheduler
        WHEN the scheduler is initialized
        THEN it receives the audit service instance.

        PYTEST-XDIST FIX (2025-12-16): Use side_effect with factory function
        instead of return_value to prevent MagicMock pollution across xdist workers.
        """
        from mcp_server_langgraph.app import create_app

        test_settings = Settings(
            audit_scheduler_enabled=True,
            audit_scheduler_hours=24,
            environment="test",
        )

        # PYTEST-XDIST FIX: Track call kwargs via mutable container
        call_tracker = {"create_kwargs": None, "audit_service_instance": None}

        # Create a unique mock audit service to verify it's passed through
        mock_audit_service = MagicMock()
        mock_audit_service._test_marker = "unique_audit_service"
        call_tracker["audit_service_instance"] = mock_audit_service

        def create_mock_scheduler(**kwargs):
            """Factory function to create fresh mock scheduler for each call."""
            call_tracker["create_kwargs"] = kwargs
            mock = MagicMock()

            async def mock_start():
                pass

            def mock_stop():
                pass

            mock.start = mock_start
            mock.stop = mock_stop
            return mock

        with (
            patch(
                "mcp_server_langgraph.app.create_audit_scheduler",
                side_effect=create_mock_scheduler,
            ),
            patch(
                "mcp_server_langgraph.app.get_audit_service",
                side_effect=lambda: call_tracker["audit_service_instance"],
            ),
        ):
            app = create_app(
                settings_override=test_settings,
                skip_startup_validation=True,
            )

            with TestClient(app):
                pass

            # Verify audit_service was passed
            assert call_tracker["create_kwargs"] is not None, "create_audit_scheduler should have been called"
            assert "audit_service" in call_tracker["create_kwargs"]
            assert call_tracker["create_kwargs"]["audit_service"] is mock_audit_service
