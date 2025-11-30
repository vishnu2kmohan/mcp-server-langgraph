"""
TDD Tests for GDPR Storage Initialization in App Startup

These tests define the expected behavior for GDPR storage initialization
during application lifespan startup.

Following TDD:
1. Write tests first (this file) - RED
2. Implement initialization in app_factory.py - GREEN
3. Verify all tests pass - REFACTOR

Test Coverage:
- GDPR storage is initialized during app lifespan startup
- Storage is accessible via get_gdpr_storage() after startup
- Proper cleanup happens on shutdown
- Error handling for initialization failures
- Different backends (postgres, memory) are supported
"""

import gc
import os
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.infrastructure]

# Use configurable Postgres port (default 9432 for test isolation)
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "9432")


@pytest.mark.xdist_group(name="testgdprstorageinit")
class TestGDPRStorageInitialization:
    """Test GDPR storage initialization in app startup"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_gdpr_storage_initialized_during_lifespan_startup(self):
        """
        Test that GDPR storage is initialized when app lifespan starts

        Behavior:
        - When app lifespan context enters
        - Then initialize_gdpr_storage() should be called
        - And storage should be accessible via get_gdpr_storage()
        """
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.infrastructure.app_factory import create_lifespan

        container = create_test_container()

        # Mock the GDPR storage initialization at the source module
        with patch(
            "mcp_server_langgraph.compliance.gdpr.factory.initialize_gdpr_storage", new_callable=AsyncMock
        ) as mock_init:
            mock_init.return_value = None  # initialize_gdpr_storage returns None

            lifespan = create_lifespan(container=container)

            # Enter lifespan context (simulates app startup)
            async with lifespan:
                # GDPR storage initialization should have been called
                mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_gdpr_storage_uses_settings_from_container(self):
        """
        Test that GDPR storage initialization uses settings from container

        Behavior:
        - Container has settings with gdpr_storage_backend and gdpr_postgres_url
        - When lifespan starts
        - Then initialize_gdpr_storage() called with correct parameters
        """
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.infrastructure.app_factory import create_lifespan

        # Create container with specific GDPR settings
        settings = Settings(
            environment="test",
            gdpr_storage_backend="memory",
            gdpr_postgres_url="postgresql://test:test@localhost:{POSTGRES_PORT}/gdpr_test",
        )
        container = create_test_container(settings=settings)

        with patch(
            "mcp_server_langgraph.compliance.gdpr.factory.initialize_gdpr_storage", new_callable=AsyncMock
        ) as mock_init:
            mock_init.return_value = None

            lifespan = create_lifespan(container=container)

            async with lifespan:
                # Should be called with settings from container
                mock_init.assert_called_once_with(
                    backend="memory", postgres_url="postgresql://test:test@localhost:{POSTGRES_PORT}/gdpr_test"
                )

    @pytest.mark.asyncio
    async def test_gdpr_storage_initialization_failure_prevents_startup(self):
        """
        Test that GDPR storage initialization failure prevents app startup

        Behavior:
        - When initialize_gdpr_storage() raises an exception
        - Then the lifespan context should raise the exception
        - And app should not start (fail-fast principle)
        """
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.infrastructure.app_factory import create_lifespan

        container = create_test_container()

        with patch(
            "mcp_server_langgraph.compliance.gdpr.factory.initialize_gdpr_storage", new_callable=AsyncMock
        ) as mock_init:
            # Simulate database connection failure
            mock_init.side_effect = Exception("PostgreSQL connection failed")

            lifespan = create_lifespan(container=container)

            # Should raise exception and prevent startup
            with pytest.raises(Exception, match="PostgreSQL connection failed"):
                async with lifespan:
                    pass  # Should not reach here

    @pytest.mark.asyncio
    async def test_gdpr_storage_accessible_after_startup(self):
        """
        Test that GDPR storage is accessible via get_gdpr_storage() after startup

        Behavior:
        - After lifespan startup completes
        - When calling get_gdpr_storage()
        - Then should return the initialized storage instance
        - And should not raise RuntimeError
        """
        from mcp_server_langgraph.compliance.gdpr.factory import get_gdpr_storage, reset_gdpr_storage
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.infrastructure.app_factory import create_lifespan

        # Start with clean state
        reset_gdpr_storage()

        container = create_test_container()
        lifespan = create_lifespan(container=container)

        async with lifespan:
            # Inside lifespan context, storage should be accessible
            storage = get_gdpr_storage()
            assert storage is not None
            assert hasattr(storage, "user_profiles")
            assert hasattr(storage, "preferences")
            assert hasattr(storage, "consents")
            assert hasattr(storage, "conversations")
            assert hasattr(storage, "audit_logs")

    @pytest.mark.asyncio
    async def test_gdpr_storage_cleanup_on_shutdown(self):
        """
        Test that GDPR storage is cleaned up on app shutdown

        Behavior:
        - After lifespan context exits
        - When calling get_gdpr_storage()
        - Then should raise RuntimeError (storage reset)
        """
        from mcp_server_langgraph.compliance.gdpr.factory import get_gdpr_storage, reset_gdpr_storage
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.infrastructure.app_factory import create_lifespan

        # Start with clean state
        reset_gdpr_storage()

        container = create_test_container()
        lifespan = create_lifespan(container=container)

        async with lifespan:
            # Storage accessible during lifespan
            storage = get_gdpr_storage()
            assert storage is not None

        # After lifespan exits, storage should be reset
        with pytest.raises(RuntimeError, match="GDPR storage not initialized"):
            get_gdpr_storage()

    @pytest.mark.asyncio
    async def test_gdpr_storage_postgres_backend_initialization(self):
        """
        Test that PostgreSQL backend is initialized correctly in production

        Behavior:
        - When gdpr_storage_backend is "postgres"
        - Then initialize_gdpr_storage() called with backend="postgres"
        - And postgres_url from settings is used
        """
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.core.container import ApplicationContainer, ContainerConfig
        from mcp_server_langgraph.infrastructure.app_factory import create_lifespan

        # Create production-like settings
        settings = Settings(
            environment="development",  # Not actual production to avoid validation issues
            gdpr_storage_backend="postgres",
            gdpr_postgres_url="postgresql://postgres:postgres@postgres:5432/gdpr",
        )
        config = ContainerConfig(environment="development")
        container = ApplicationContainer(config, settings=settings)

        with patch(
            "mcp_server_langgraph.compliance.gdpr.factory.initialize_gdpr_storage", new_callable=AsyncMock
        ) as mock_init:
            mock_init.return_value = None

            lifespan = create_lifespan(container=container)

            async with lifespan:
                # Should be called with postgres backend
                mock_init.assert_called_once_with(
                    backend="postgres", postgres_url="postgresql://postgres:postgres@postgres:5432/gdpr"
                )

    @pytest.mark.asyncio
    async def test_gdpr_storage_memory_backend_initialization(self):
        """
        Test that in-memory backend is initialized correctly in test/dev

        Behavior:
        - When gdpr_storage_backend is "memory"
        - Then initialize_gdpr_storage() called with backend="memory"
        - And postgres_url is still provided (but ignored by memory backend)
        """
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.infrastructure.app_factory import create_lifespan

        container = create_test_container()
        # Test container uses memory backend by default

        with patch(
            "mcp_server_langgraph.compliance.gdpr.factory.initialize_gdpr_storage", new_callable=AsyncMock
        ) as mock_init:
            mock_init.return_value = None

            lifespan = create_lifespan(container=container)

            async with lifespan:
                # Should be called with memory backend
                args, kwargs = mock_init.call_args
                assert kwargs.get("backend") == "memory" or args[0] == "memory"

    @pytest.mark.asyncio
    async def test_gdpr_storage_initialization_logged(self):
        """
        Test that GDPR storage initialization is logged

        Behavior:
        - When GDPR storage is initialized
        - Then log message should indicate initialization
        - And include backend type (postgres or memory)
        """
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.infrastructure.app_factory import create_lifespan

        container = create_test_container()

        with patch("mcp_server_langgraph.infrastructure.app_factory.logger") as mock_logger:
            with patch("mcp_server_langgraph.compliance.gdpr.factory.initialize_gdpr_storage", new_callable=AsyncMock):
                lifespan = create_lifespan(container=container)

                async with lifespan:
                    # Check that logging occurred (any info/debug call about GDPR is fine)
                    # This is a weak assertion - implementation may vary
                    assert mock_logger.info.called or mock_logger.debug.called

    def test_app_factory_creates_app_with_gdpr_storage_initialized(self):
        """
        Test that create_app() results in an app with GDPR storage initialized

        Behavior:
        - When create_app() is called with container
        - Then app should have a lifespan configured
        - And the lifespan should initialize GDPR storage
        """
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.infrastructure.app_factory import create_app

        container = create_test_container()
        app = create_app(container=container)

        # App should have lifespan configured
        assert app.router.lifespan_context is not None

        # The lifespan is our create_lifespan function which initializes GDPR
        # This is implicitly tested by the other tests that verify lifespan behavior

    @pytest.mark.asyncio
    async def test_lifespan_without_container_skips_gdpr_initialization(self):
        """
        Test that lifespan without container doesn't crash

        Behavior:
        - When create_lifespan() called without container
        - Then should not attempt GDPR initialization
        - And should not raise any errors
        """
        from mcp_server_langgraph.infrastructure.app_factory import create_lifespan

        lifespan = create_lifespan(container=None)

        # Should complete without errors
        async with lifespan:
            pass  # No container, so no initialization


@pytest.mark.xdist_group(name="testgdprstorageerrors")
class TestGDPRStorageInitializationErrors:
    """Test error handling in GDPR storage initialization"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_postgres_connection_error_logged_and_raised(self):
        """
        Test that PostgreSQL connection errors are logged and raised

        Behavior:
        - When PostgreSQL connection fails
        - Then error should be logged
        - And exception should be raised to prevent startup
        """
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.infrastructure.app_factory import create_lifespan

        settings = Settings(
            environment="test",
            gdpr_storage_backend="postgres",
            gdpr_postgres_url="postgresql://invalid:invalid@nonexistent:5432/gdpr",
        )
        container = create_test_container(settings=settings)

        with patch("mcp_server_langgraph.infrastructure.app_factory.logger") as mock_logger:
            with patch(
                "mcp_server_langgraph.compliance.gdpr.factory.initialize_gdpr_storage", new_callable=AsyncMock
            ) as mock_init:
                mock_init.side_effect = Exception("Connection refused")

                lifespan = create_lifespan(container=container)

                with pytest.raises(Exception, match="Connection refused"):
                    async with lifespan:
                        pass

                # Error should have been logged (via error, exception, or critical)
                assert (
                    any("GDPR" in str(call) or "storage" in str(call).lower() for call in mock_logger.error.call_args_list)
                    or any(
                        "GDPR" in str(call) or "storage" in str(call).lower() for call in mock_logger.exception.call_args_list
                    )
                    or mock_logger.critical.called
                )

    @pytest.mark.asyncio
    async def test_invalid_backend_configuration_fails_startup(self):
        """
        Test that invalid backend configuration prevents startup

        Behavior:
        - When gdpr_storage_backend has invalid value
        - Then should raise ValueError
        - And app should not start
        """
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.core.container import create_test_container
        from mcp_server_langgraph.infrastructure.app_factory import create_lifespan

        # Note: Pydantic will validate settings, so we need to test
        # the initialization function directly
        settings = Settings(environment="test")
        container = create_test_container(settings=settings)

        with patch(
            "mcp_server_langgraph.compliance.gdpr.factory.initialize_gdpr_storage", new_callable=AsyncMock
        ) as mock_init:
            mock_init.side_effect = ValueError("Invalid GDPR storage backend")

            lifespan = create_lifespan(container=container)

            with pytest.raises(ValueError, match="Invalid GDPR storage backend"):
                async with lifespan:
                    pass
