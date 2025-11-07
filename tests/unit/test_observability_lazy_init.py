"""
Unit tests for lazy observability initialization.

Tests verify that observability can be imported without triggering
filesystem operations or requiring configuration at import time.
"""

import os
import tempfile
from pathlib import Path

import pytest


@pytest.mark.unit
def test_import_without_filesystem_ops():
    """
    Test that importing observability module doesn't create files.

    This is critical for:
    - Library usage (embedding in other packages)
    - Read-only containers
    - Serverless environments
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Change to temporary directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Reset observability state to simulate fresh import
            import mcp_server_langgraph.observability.telemetry as telemetry

            telemetry._observability_config = None
            telemetry._propagator = None

            # Verify no logs directory was created
            assert not Path("logs").exists(), "logs/ directory should not be created on import"

            # Verify observability is not initialized after reset
            assert not telemetry.is_initialized(), "Observability should not be initialized on import"

        finally:
            os.chdir(original_cwd)


@pytest.mark.unit
def test_lazy_accessors_raise_before_init():
    """
    Test that lazy accessors raise RuntimeError before initialization.
    """
    # Reset observability state
    import mcp_server_langgraph.observability.telemetry as telemetry_module

    telemetry_module._observability_config = None
    telemetry_module._propagator = None

    # Accessing logger/tracer/meter should raise RuntimeError
    with pytest.raises((RuntimeError, AttributeError)):
        from mcp_server_langgraph.observability.telemetry import logger

        logger.info("This should fail")

    with pytest.raises((RuntimeError, AttributeError)):
        from mcp_server_langgraph.observability.telemetry import tracer

        tracer.start_as_current_span("test")

    with pytest.raises((RuntimeError, AttributeError)):
        from mcp_server_langgraph.observability.telemetry import meter

        meter.create_counter("test")


@pytest.mark.unit
def test_init_observability_with_defaults():
    """
    Test that init_observability works with default parameters.
    """
    # Reset state
    import mcp_server_langgraph.observability.telemetry as telemetry_module
    from mcp_server_langgraph.observability.telemetry import init_observability, is_initialized

    telemetry_module._observability_config = None

    # Initialize with defaults (no file logging)
    config = init_observability(enable_file_logging=False)

    assert is_initialized(), "Observability should be initialized"
    assert config is not None
    assert config.service_name == "mcp-server-langgraph"
    assert config.enable_file_logging is False


@pytest.mark.unit
def test_init_observability_with_settings():
    """
    Test that init_observability respects settings configuration.
    """
    from mcp_server_langgraph.core.config import Settings
    from mcp_server_langgraph.observability.telemetry import init_observability

    # Create custom settings
    settings = Settings(
        log_format="text",
        langsmith_tracing=False,
        observability_backend="opentelemetry",
        enable_file_logging=False,
    )

    # Reset state
    import mcp_server_langgraph.observability.telemetry as telemetry_module

    telemetry_module._observability_config = None

    # Initialize with custom settings
    config = init_observability(settings=settings)

    assert config.log_format == "text"
    assert config.enable_langsmith is False
    assert config.enable_file_logging is False


@pytest.mark.unit
def test_init_observability_idempotent():
    """
    Test that calling init_observability multiple times is safe.
    """
    # Reset state
    import mcp_server_langgraph.observability.telemetry as telemetry_module
    from mcp_server_langgraph.observability.telemetry import init_observability

    telemetry_module._observability_config = None

    # First call
    config1 = init_observability(enable_file_logging=False)

    # Second call should return same config
    config2 = init_observability(enable_file_logging=False)

    assert config1 is config2, "Multiple init calls should return same config instance"


@pytest.mark.unit
def test_file_logging_opt_in():
    """
    Test that file logging is opt-in and doesn't create files by default.
    """
    from mcp_server_langgraph.observability.telemetry import init_observability

    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Reset state
            import mcp_server_langgraph.observability.telemetry as telemetry_module

            telemetry_module._observability_config = None

            # Initialize WITHOUT file logging (default)
            init_observability(enable_file_logging=False)

            # Verify logs directory was NOT created
            assert not Path("logs").exists(), "logs/ directory should not be created when file logging is disabled"

        finally:
            os.chdir(original_cwd)


@pytest.mark.unit
def test_file_logging_creates_directory_when_enabled():
    """
    Test that file logging creates logs/ when explicitly enabled.
    """
    import logging

    from mcp_server_langgraph.observability.telemetry import init_observability

    with tempfile.TemporaryDirectory() as tmpdir:
        original_cwd = os.getcwd()
        try:
            os.chdir(tmpdir)

            # Reset state - must clear both observability config AND logging handlers
            import mcp_server_langgraph.observability.telemetry as telemetry_module

            telemetry_module._observability_config = None

            # Clear root logger handlers to allow re-initialization
            root_logger = logging.getLogger()
            root_logger.handlers.clear()

            # Initialize WITH file logging
            init_observability(enable_file_logging=True)

            # Verify logs directory WAS created
            assert Path("logs").exists(), "logs/ directory should be created when file logging is enabled"

        finally:
            os.chdir(original_cwd)


@pytest.mark.unit
def test_lazy_accessors_work_after_init():
    """
    Test that lazy accessors work correctly after initialization.
    """
    # Reset state
    import mcp_server_langgraph.observability.telemetry as telemetry_module
    from mcp_server_langgraph.observability.telemetry import init_observability, logger, meter, tracer

    telemetry_module._observability_config = None

    # Initialize
    init_observability(enable_file_logging=False)

    # Logger should work
    logger.info("Test message")

    # Tracer should work
    with tracer.start_as_current_span("test_span") as span:
        assert span is not None

    # Meter should work
    counter = meter.create_counter("test_counter", description="Test counter", unit="1")
    assert counter is not None


@pytest.mark.unit
def test_settings_values_honored():
    """
    Test that settings.log_format and langsmith_tracing are honored.

    This was the original bug - settings were not available during
    import-time initialization.
    """
    # Reset state
    import mcp_server_langgraph.observability.telemetry as telemetry_module
    from mcp_server_langgraph.core.config import Settings
    from mcp_server_langgraph.observability.telemetry import init_observability

    telemetry_module._observability_config = None

    # Create settings with specific values
    settings = Settings(
        log_format="json",
        log_json_indent=2,
        langsmith_tracing=True,
        observability_backend="both",
        enable_file_logging=False,
    )

    # Initialize with settings
    config = init_observability(settings=settings)

    # Verify settings were honored
    assert config.log_format == "json"
    assert config.log_json_indent == 2
    assert config.enable_langsmith is True


@pytest.mark.unit
def test_secrets_manager_works_before_observability_init():
    """
    Test that secrets manager can be used before observability is initialized.

    This verifies the circular import fix:
    config -> secrets.manager -> telemetry -> config
    """
    # Reset observability state
    import mcp_server_langgraph.observability.telemetry as telemetry_module

    telemetry_module._observability_config = None
    telemetry_module._propagator = None

    # Secrets manager should work even without observability
    from mcp_server_langgraph.secrets.manager import SecretsManager

    # Should not raise any errors
    manager = SecretsManager()

    # Should use stdlib logging, not observability logging
    # (We can't easily test this without mocking, but at least verify it doesn't crash)
    assert manager is not None


@pytest.mark.unit
def test_context_propagation_requires_init():
    """
    Test that context propagation functions require initialization.
    """
    # Reset state
    import mcp_server_langgraph.observability.telemetry as telemetry_module
    from mcp_server_langgraph.observability.telemetry import extract_context, inject_context

    telemetry_module._observability_config = None
    telemetry_module._propagator = None

    # Should raise RuntimeError
    carrier = {}
    with pytest.raises(RuntimeError, match="Observability not initialized"):
        inject_context(carrier)

    with pytest.raises(RuntimeError, match="Observability not initialized"):
        extract_context(carrier)


@pytest.mark.unit
def test_multiple_entry_points_can_init():
    """
    Test that multiple entry points can safely call init_observability.

    Simulates scenario where both server_stdio.py and other entry point
    call init_observability.
    """
    # Reset state
    import mcp_server_langgraph.observability.telemetry as telemetry_module
    from mcp_server_langgraph.observability.telemetry import init_observability, is_initialized

    telemetry_module._observability_config = None

    # First entry point initializes
    config1 = init_observability(enable_file_logging=False)
    assert is_initialized()

    # Second entry point also calls init (should be no-op)
    config2 = init_observability(enable_file_logging=False)
    assert config1 is config2

    # Still initialized
    assert is_initialized()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
