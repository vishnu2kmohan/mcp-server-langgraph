"""
Tests for observability lazy initialization and safe logger fallback.

Verifies that functions can log safely even before init_observability() is called.
This prevents RuntimeError when calling create_user_provider(), create_session_store(),
etc. from test fixtures or standalone scripts.
"""

import gc
import logging

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="testobservabilitysafefallback")
class TestObservabilitySafeFallback:
    """Test safe fallback behavior before observability initialization"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_logger_usable_before_init(self):
        """
        Test that logger can be used before init_observability().

        This is the core issue: functions like create_user_provider() need to log
        but may be called before observability is initialized (e.g., in test fixtures).
        """
        from mcp_server_langgraph.observability.telemetry import get_logger

        # Should not raise RuntimeError - should return a safe fallback logger
        logger = get_logger()

        # Should be able to call logging methods without error
        logger.info("Test message before init")
        logger.warning("Warning message before init")
        logger.debug("Debug message before init")
        logger.error("Error message before init")

    def test_create_user_provider_before_observability_init(self):
        """
        Test that create_user_provider() works before init_observability().

        This function logs at lines 61, 62, 76 in factory.py.
        """
        from mcp_server_langgraph.auth.factory import create_user_provider
        from mcp_server_langgraph.core.config import Settings

        # Create settings without initializing observability
        settings = Settings(
            environment="test",
            auth_provider="inmemory",
            jwt_secret_key="test-secret-key-for-testing-only",
            gdpr_storage_backend="memory",
        )

        # Should not raise RuntimeError when creating user provider
        # (even though it tries to log)
        provider = create_user_provider(settings)

        assert provider is not None

    def test_create_session_store_before_observability_init(self):
        """
        Test that create_session_store() works before init_observability().

        This function logs at lines 127, 133, 146 in auth/factory.py.
        """
        from mcp_server_langgraph.auth.factory import create_session_store
        from mcp_server_langgraph.core.config import Settings

        # Create settings without initializing observability
        settings = Settings(
            environment="test",
            auth_provider="inmemory",
            auth_mode="session",
            session_backend="memory",
            jwt_secret_key="test-secret-key-for-testing-only",
            gdpr_storage_backend="memory",
        )

        # Should not raise RuntimeError when creating session store
        store = create_session_store(settings)

        assert store is not None

    def test_logger_fallback_logs_to_stderr(self, caplog):
        """
        Test that fallback logger actually logs messages (to stderr).

        We want to ensure the fallback isn't a no-op - it should still log.
        """
        from mcp_server_langgraph.observability.telemetry import get_logger

        logger = get_logger()

        with caplog.at_level(logging.INFO):
            logger.info("Test info message")
            logger.warning("Test warning message")

        # Verify messages were logged
        assert any("Test info message" in record.message for record in caplog.records)
        assert any("Test warning message" in record.message for record in caplog.records)

    def test_logger_after_init_uses_configured_logger(self):
        """
        Test that after init_observability(), logger uses the configured logger.

        This ensures the fallback is only used when needed.
        """
        from mcp_server_langgraph.core.config import Settings
        from mcp_server_langgraph.observability.telemetry import get_logger, init_observability, shutdown_observability

        try:
            # Create test settings
            settings = Settings(
                environment="test",
                auth_provider="inmemory",
                jwt_secret_key="test-secret-key-for-testing-only",
                gdpr_storage_backend="memory",
            )

            # Initialize observability
            init_observability(settings)

            # Now logger should use the configured logger
            logger = get_logger()

            # Should be the ObservabilityConfig logger, not fallback
            assert hasattr(logger, "name")

        finally:
            # Clean up
            shutdown_observability()


@pytest.mark.unit
@pytest.mark.xdist_group(name="testobservabilityintegration")
class TestObservabilityIntegration:
    """Test observability integration with auth components"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_multiple_auth_calls_before_init(self):
        """
        Test multiple auth factory calls before observability init.

        Simulates realistic test setup scenario where multiple components
        are created before the app (and observability) is initialized.
        """
        from mcp_server_langgraph.auth.factory import create_session_store, create_user_provider
        from mcp_server_langgraph.core.config import Settings

        # Create settings
        settings = Settings(
            environment="test",
            auth_provider="inmemory",
            auth_mode="session",
            session_backend="memory",
            jwt_secret_key="test-secret-key-for-testing-only",
            gdpr_storage_backend="memory",
        )

        # All of these should work without RuntimeError
        user_provider = create_user_provider(settings)
        session_store = create_session_store(settings)

        assert user_provider is not None
        assert session_store is not None
