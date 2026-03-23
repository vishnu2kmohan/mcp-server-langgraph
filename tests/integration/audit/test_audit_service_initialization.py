"""
Tests for audit service initialization during app bootstrap.

Tests verify that bootstrap/storage.py correctly initializes:
- UnifiedAuditService during app startup
- set_audit_service() for middleware access
- Repository selection (InMemory vs Postgres)
- Retention scheduler lifecycle

Architecture: create_app() → lifespan → bootstrap_all() → init_storage()
init_storage() creates audit repo, audit service, calls set_audit_service(),
and conditionally starts retention scheduler based on settings.
"""

import gc
from unittest.mock import AsyncMock, MagicMock, patch

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
    calls init_storage. This lets tests focus on audit service behavior
    without requiring 8+ other infrastructure services.
    """

    async def mock_bootstrap_all(settings):
        from mcp_server_langgraph.bootstrap import AppState
        from mcp_server_langgraph.bootstrap.storage import init_storage

        storage = await init_storage(settings)
        return AppState(storage=storage)

    return mock_bootstrap_all


@pytest.mark.integration
@pytest.mark.xdist_group(name="audit_service_init")
class TestAuditServiceInitialization:
    """Tests for audit service initialization."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_audit_service_created_on_startup(self) -> None:
        """
        GIVEN app starts
        WHEN initialization completes
        THEN audit service is created and available.
        """
        from mcp_server_langgraph.app import create_app
        from mcp_server_langgraph.middleware.audit import get_audit_service

        test_settings = Settings(
            environment="test",
        )

        # Reset global audit service before test
        with (
            patch(
                "mcp_server_langgraph.middleware.audit._audit_service",
                None,
            ),
            patch(
                "mcp_server_langgraph.app.bootstrap_all",
                side_effect=_make_storage_only_bootstrap(),
            ),
            patch(
                "mcp_server_langgraph.audit.repository.create_audit_repository",
                return_value=MagicMock(),
            ),
        ):
            app = create_app(
                settings_override=test_settings,
                skip_startup_validation=True,
            )

            with TestClient(app):
                # Audit service should be available
                service = get_audit_service()
                assert service is not None

    def test_audit_service_set_via_set_audit_service(self) -> None:
        """
        GIVEN app starts
        WHEN initialization completes
        THEN set_audit_service was called.

        init_storage() calls set_audit_service() after creating the audit service
        (moved from app.py to bootstrap/storage.py).
        """
        from mcp_server_langgraph.app import create_app

        test_settings = Settings(
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
            patch("mcp_server_langgraph.middleware.audit.set_audit_service") as mock_set_service,
        ):
            app = create_app(
                settings_override=test_settings,
                skip_startup_validation=True,
            )

            with TestClient(app):
                pass

            # set_audit_service should have been called by init_storage
            mock_set_service.assert_called_once()

    def test_audit_service_uses_integrity_secret(self) -> None:
        """
        GIVEN app with audit_integrity_secret configured
        WHEN audit service is created
        THEN service uses the configured secret.

        init_storage() creates UnifiedAuditService with integrity_secret
        from settings (moved from app.py to bootstrap/storage.py).
        """
        from mcp_server_langgraph.app import create_app

        test_settings = Settings(
            environment="test",
            audit_integrity_secret="test-integrity-secret-12345",
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
            patch("mcp_server_langgraph.audit.service.UnifiedAuditService") as mock_service_class,
        ):
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            app = create_app(
                settings_override=test_settings,
                skip_startup_validation=True,
            )

            with TestClient(app):
                pass

            # Verify audit_integrity_secret was passed
            mock_service_class.assert_called_once()
            call_kwargs = mock_service_class.call_args[1]
            assert call_kwargs["integrity_secret"] == "test-integrity-secret-12345"


@pytest.mark.integration
@pytest.mark.xdist_group(name="audit_service_init")
class TestAuditRepositorySelection:
    """Tests for audit repository selection based on environment."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_uses_factory_to_create_repository(self) -> None:
        """
        GIVEN audit service initialization
        WHEN app is created
        THEN uses create_audit_repository factory to select appropriate repository.

        init_storage() calls create_audit_repository(database_url=settings.database_url)
        (moved from app.py to bootstrap/storage.py).
        """
        from mcp_server_langgraph.app import create_app
        from mcp_server_langgraph.audit.repository import InMemoryUnifiedAuditRepository

        test_settings = Settings(
            environment="test",
        )

        with (
            patch(
                "mcp_server_langgraph.app.bootstrap_all",
                side_effect=_make_storage_only_bootstrap(),
            ),
            patch("mcp_server_langgraph.audit.repository.create_audit_repository") as mock_factory,
        ):
            mock_repo = MagicMock(spec=InMemoryUnifiedAuditRepository)
            mock_factory.return_value = mock_repo

            app = create_app(
                settings_override=test_settings,
                skip_startup_validation=True,
            )

            with TestClient(app):
                pass

            # Factory should be called with database_url from settings
            mock_factory.assert_called_once()
            call_kwargs = mock_factory.call_args[1]
            assert "database_url" in call_kwargs


@pytest.mark.integration
@pytest.mark.xdist_group(name="audit_service_init")
class TestAuditServiceMiddlewareIntegration:
    """Tests for audit service integration with middleware."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_middleware_receives_audit_service(self) -> None:
        """
        GIVEN app with audit middleware
        WHEN request is processed
        THEN middleware has access to audit service.
        """
        from mcp_server_langgraph.app import create_app
        from mcp_server_langgraph.middleware.audit import get_audit_service

        test_settings = Settings(
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
        ):
            app = create_app(
                settings_override=test_settings,
                skip_startup_validation=True,
            )

            with TestClient(app) as client:
                # Make a request to trigger middleware
                client.get("/health")

                # Audit service should be available
                service = get_audit_service()
                assert service is not None


@pytest.mark.integration
@pytest.mark.xdist_group(name="audit_service_init")
class TestRetentionSchedulerIntegration:
    """Tests for partition retention scheduler integration in lifespan."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_retention_scheduler_started_when_enabled(self) -> None:
        """
        GIVEN partition_retention_enabled=True
        WHEN app starts
        THEN retention scheduler is started.

        init_storage() creates and starts retention scheduler based on
        settings.partition_retention_enabled (moved from app.py to bootstrap/storage.py).
        """
        from mcp_server_langgraph.app import create_app

        test_settings = Settings(
            environment="test",
            partition_retention_enabled=True,
            partition_retention_months=84,
            partition_retention_hours=24,
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
            patch("mcp_server_langgraph.audit.retention_scheduler.create_retention_scheduler") as mock_create_scheduler,
        ):
            mock_scheduler = AsyncMock(return_value=None)  # async-mock-configured
            mock_scheduler.start = AsyncMock(return_value=None)  # async-mock-configured
            mock_scheduler.stop = AsyncMock(return_value=None)  # async-mock-configured
            mock_create_scheduler.return_value = mock_scheduler

            app = create_app(
                settings_override=test_settings,
                skip_startup_validation=True,
            )

            with TestClient(app):
                pass

            # Scheduler should have been created with correct parameters
            mock_create_scheduler.assert_called_once_with(
                retention_months=84,
                schedule_hours=24,
            )
            # Scheduler should have been started
            mock_scheduler.start.assert_called_once()

    def test_retention_scheduler_not_started_when_disabled(self) -> None:
        """
        GIVEN partition_retention_enabled=False
        WHEN app starts
        THEN retention scheduler is NOT started.
        """
        from mcp_server_langgraph.app import create_app

        test_settings = Settings(
            environment="test",
            partition_retention_enabled=False,
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
            patch("mcp_server_langgraph.audit.retention_scheduler.create_retention_scheduler") as mock_create_scheduler,
        ):
            app = create_app(
                settings_override=test_settings,
                skip_startup_validation=True,
            )

            with TestClient(app):
                pass

            # Scheduler should NOT have been created
            mock_create_scheduler.assert_not_called()

    def test_retention_scheduler_stopped_on_shutdown(self) -> None:
        """
        GIVEN retention scheduler is running
        WHEN app shuts down
        THEN scheduler is stopped gracefully.

        StorageState.cleanup() calls await retention_scheduler.stop().
        """
        from mcp_server_langgraph.app import create_app

        test_settings = Settings(
            environment="test",
            partition_retention_enabled=True,
            partition_retention_months=72,
            partition_retention_hours=12,
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
            patch("mcp_server_langgraph.audit.retention_scheduler.create_retention_scheduler") as mock_create_scheduler,
        ):
            mock_scheduler = AsyncMock(return_value=None)  # async-mock-configured
            mock_scheduler.start = AsyncMock(return_value=None)  # async-mock-configured
            mock_scheduler.stop = AsyncMock(return_value=None)  # async-mock-configured
            mock_create_scheduler.return_value = mock_scheduler

            app = create_app(
                settings_override=test_settings,
                skip_startup_validation=True,
            )

            with TestClient(app):
                pass

            # Scheduler should be stopped on shutdown
            mock_scheduler.stop.assert_called_once()

    def test_retention_scheduler_uses_config_values(self) -> None:
        """
        GIVEN custom retention configuration
        WHEN scheduler is created
        THEN uses configured values.
        """
        from mcp_server_langgraph.app import create_app

        test_settings = Settings(
            environment="test",
            partition_retention_enabled=True,
            partition_retention_months=72,  # HIPAA 6 years
            partition_retention_hours=12,  # Twice daily
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
            patch("mcp_server_langgraph.audit.retention_scheduler.create_retention_scheduler") as mock_create_scheduler,
        ):
            mock_scheduler = AsyncMock(return_value=None)  # async-mock-configured
            mock_scheduler.start = AsyncMock(return_value=None)  # async-mock-configured
            mock_scheduler.stop = AsyncMock(return_value=None)  # async-mock-configured
            mock_create_scheduler.return_value = mock_scheduler

            app = create_app(
                settings_override=test_settings,
                skip_startup_validation=True,
            )

            with TestClient(app):
                pass

            # Verify config values passed to scheduler
            mock_create_scheduler.assert_called_once_with(
                retention_months=72,
                schedule_hours=12,
            )
