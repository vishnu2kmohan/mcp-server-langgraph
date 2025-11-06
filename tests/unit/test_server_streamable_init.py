"""
Unit tests for server_streamable module initialization.

Tests verify that the module can be imported without triggering
observability initialization errors (module-level logger usage).
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_server_streamable_import_without_observability_init():
    """
    Test that importing server_streamable doesn't require observability to be initialized.

    This test verifies the fix for the RuntimeError:
    "Observability not initialized. Call init_observability(settings)
    in your entry point before using observability features."

    CRITICAL: server_streamable.py should NOT use logger/tracer/metrics at module level.
    Only use them inside functions that are called AFTER lifespan initialization.
    """
    # Reset observability state to simulate fresh import
    import mcp_server_langgraph.observability.telemetry as telemetry_module

    telemetry_module._observability_config = None
    telemetry_module._propagator = None

    # Remove server_streamable from sys.modules to force re-import
    if "mcp_server_langgraph.mcp.server_streamable" in sys.modules:
        del sys.modules["mcp_server_langgraph.mcp.server_streamable"]

    # Mock settings to avoid config validation issues
    with patch("mcp_server_langgraph.core.config.settings") as mock_settings:
        mock_settings.service_version = "1.0.0"
        mock_settings.get_cors_origins.return_value = []
        mock_settings.enable_file_logging = False
        mock_settings.redis_host = "localhost"
        mock_settings.redis_port = 6379
        mock_settings.redis_password = None
        mock_settings.redis_db = 0

        # Mock rate limiter storage to avoid Redis connection
        with patch("mcp_server_langgraph.middleware.rate_limiter.storage_from_string") as mock_storage:
            mock_storage.return_value = MagicMock()

            # This should NOT raise RuntimeError about observability initialization
            try:
                import mcp_server_langgraph.mcp.server_streamable as server_streamable

                # Verify the module was imported successfully
                assert server_streamable.app is not None, "FastAPI app should be created"

            except RuntimeError as e:
                if "Observability not initialized" in str(e):
                    pytest.fail(
                        "server_streamable.py uses logger at module level before observability is initialized. "
                        "Move logger calls inside functions or use logging.getLogger(__name__) for module-level logging."
                    )
                else:
                    raise


@pytest.mark.unit
def test_rate_limiting_initialization_uses_lazy_logger():
    """
    Test that rate limiting initialization (lines 187-198) uses lazy logger correctly.

    The module-level try/except block that initializes rate limiting should:
    1. NOT cause observability initialization errors on import
    2. Log messages only after lifespan has initialized observability
    3. Use logging.getLogger() for module-level logging OR defer logging to lifespan
    """
    # Reset observability state
    import mcp_server_langgraph.observability.telemetry as telemetry_module

    telemetry_module._observability_config = None
    telemetry_module._propagator = None

    # Remove module from cache to force re-import
    if "mcp_server_langgraph.mcp.server_streamable" in sys.modules:
        del sys.modules["mcp_server_langgraph.mcp.server_streamable"]

    # Mock settings
    with patch("mcp_server_langgraph.core.config.settings") as mock_settings:
        mock_settings.service_version = "1.0.0"
        mock_settings.get_cors_origins.return_value = []
        mock_settings.enable_file_logging = False

        # Import should succeed without observability being initialized
        import mcp_server_langgraph.mcp.server_streamable

        # Observability should still not be initialized after module import
        assert (
            not telemetry_module.is_initialized()
        ), "Observability should only be initialized in lifespan, not at module import"


@pytest.mark.unit
async def test_lifespan_initializes_observability_before_logger_use():
    """
    Test that the lifespan context manager initializes observability before any logger usage.

    This ensures that:
    1. Observability is initialized in the lifespan startup event
    2. Logger can be used safely after lifespan startup
    3. Application doesn't crash on startup
    """
    # Reset state
    import mcp_server_langgraph.observability.telemetry as telemetry_module
    from mcp_server_langgraph.observability.telemetry import init_observability, is_initialized, shutdown_observability

    telemetry_module._observability_config = None

    # Remove module from cache
    if "mcp_server_langgraph.mcp.server_streamable" in sys.modules:
        del sys.modules["mcp_server_langgraph.mcp.server_streamable"]

    # Mock settings
    with patch("mcp_server_langgraph.core.config.settings") as mock_settings:
        mock_settings.service_version = "1.0.0"
        mock_settings.get_cors_origins.return_value = []
        mock_settings.enable_file_logging = False

        # Import module
        from mcp_server_langgraph.mcp.server_streamable import app, lifespan

        # Simulate lifespan startup
        async with lifespan(app):
            # After lifespan startup, observability should be initialized
            assert is_initialized(), "Observability should be initialized after lifespan startup"

            # Logger should now be usable
            from mcp_server_langgraph.observability.telemetry import logger

            logger.info("Test message after initialization")  # Should not raise

        # After lifespan shutdown, cleanup should have occurred
        # Note: shutdown_observability() is called in lifespan, so state may be reset
