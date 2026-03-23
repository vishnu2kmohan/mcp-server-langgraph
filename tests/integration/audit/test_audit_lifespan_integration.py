"""
Tests for audit scheduler integration with FastAPI app lifespan.

Tests verify that bootstrap/storage.py correctly manages audit scheduler lifecycle:
- Start the audit scheduler on app startup when enabled
- Not start the scheduler when disabled
- Stop the scheduler gracefully on app shutdown
- Use configuration from settings

Architecture: create_app() → lifespan → bootstrap_all() → init_storage()
init_storage() creates audit service, then conditionally creates and starts
audit scheduler based on settings.audit_scheduler_enabled and audit_service presence.
"""

import gc
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from mcp_server_langgraph.core.config import Settings

pytestmark = [
    pytest.mark.integration,
]


def _make_storage_only_bootstrap():
    """Create a mock bootstrap_all that only initializes storage.

    Replaces the full bootstrap_all (which initializes auth, http, websocket,
    skills, context_graph, semantic, model_sync) with a version that only
    calls init_storage. This lets tests focus on audit scheduler behavior
    without requiring 8+ other infrastructure services.
    """

    async def mock_bootstrap_all(settings):
        from mcp_server_langgraph.bootstrap import AppState
        from mcp_server_langgraph.bootstrap.storage import init_storage

        storage = await init_storage(settings)
        return AppState(storage=storage)

    return mock_bootstrap_all


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
                "mcp_server_langgraph.app.bootstrap_all",
                side_effect=_make_storage_only_bootstrap(),
            ),
            patch(
                "mcp_server_langgraph.audit.repository.create_audit_repository",
                return_value=MagicMock(),
            ),
            patch(
                "mcp_server_langgraph.audit.factory.create_audit_scheduler",
                side_effect=create_mock_scheduler,
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

        with (
            patch(
                "mcp_server_langgraph.app.bootstrap_all",
                side_effect=_make_storage_only_bootstrap(),
            ),
            patch(
                "mcp_server_langgraph.audit.repository.create_audit_repository",
                return_value=MagicMock(),
            ),
            patch("mcp_server_langgraph.audit.factory.create_audit_scheduler") as mock_create_scheduler,
        ):
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
                "mcp_server_langgraph.app.bootstrap_all",
                side_effect=_make_storage_only_bootstrap(),
            ),
            patch(
                "mcp_server_langgraph.audit.repository.create_audit_repository",
                return_value=MagicMock(),
            ),
            patch(
                "mcp_server_langgraph.audit.factory.create_audit_scheduler",
                side_effect=create_mock_scheduler,
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
                "mcp_server_langgraph.app.bootstrap_all",
                side_effect=_make_storage_only_bootstrap(),
            ),
            patch(
                "mcp_server_langgraph.audit.repository.create_audit_repository",
                return_value=MagicMock(),
            ),
            patch(
                "mcp_server_langgraph.audit.factory.create_audit_scheduler",
                side_effect=create_mock_scheduler,
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
        GIVEN audit_scheduler_enabled=True but audit service creation fails
        WHEN the app starts
        THEN the scheduler is NOT started (graceful degradation).

        init_storage wraps audit creation in try/except. When create_audit_repository
        raises, audit_service stays None, and the scheduler condition
        (audit_scheduler_enabled AND audit_service is not None) fails.
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
                "mcp_server_langgraph.app.bootstrap_all",
                side_effect=_make_storage_only_bootstrap(),
            ),
            patch(
                "mcp_server_langgraph.audit.repository.create_audit_repository",
                side_effect=Exception("DB unavailable"),
            ),
            patch(
                "mcp_server_langgraph.audit.factory.create_audit_scheduler",
                side_effect=mock_create_scheduler_tracking,
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
                "mcp_server_langgraph.app.bootstrap_all",
                side_effect=_make_storage_only_bootstrap(),
            ),
            patch(
                "mcp_server_langgraph.audit.repository.create_audit_repository",
                return_value=MagicMock(),
            ),
            patch(
                "mcp_server_langgraph.audit.factory.create_audit_scheduler",
                side_effect=create_mock_scheduler,
            ),
        ):
            app = create_app(
                settings_override=test_settings,
                skip_startup_validation=True,
            )

            with TestClient(app):
                pass

            # Verify audit_service was passed to create_audit_scheduler
            assert call_tracker["create_kwargs"] is not None, "create_audit_scheduler should have been called"
            assert "audit_service" in call_tracker["create_kwargs"]
            # init_storage creates a real UnifiedAuditService with the mock repo
            assert call_tracker["create_kwargs"]["audit_service"] is not None
