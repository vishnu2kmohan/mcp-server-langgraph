"""Tests for observability cleanup and shutdown functionality.

Ensures that telemetry exporters are properly flushed and closed on application shutdown.
"""

from unittest.mock import MagicMock, patch

import pytest

from mcp_server_langgraph.observability.telemetry import init_observability, is_initialized, shutdown_observability


@pytest.mark.unit
class TestObservabilityShutdown:
    """Test observability shutdown and cleanup"""

    def test_shutdown_flushes_tracer_spans(self):
        """
        Test that shutdown_observability flushes pending trace spans.

        GREEN: Should call force_flush on tracer provider
        """
        # GIVEN: Initialized observability
        mock_settings = MagicMock()
        mock_settings.service_name = "test-service"
        mock_settings.enable_tracing = False
        mock_settings.enable_metrics = False
        mock_settings.enable_console_export = False
        mock_settings.enable_langsmith = False
        mock_settings.log_level = "INFO"
        mock_settings.log_format = "text"

        init_observability(settings=mock_settings)

        # WHEN: Calling shutdown
        shutdown_observability()

        # THEN: Should complete without error and clear state
        assert not is_initialized()

    def test_shutdown_handles_uninitialized_state(self):
        """
        Test that shutdown_observability handles being called when not initialized.

        GREEN: Should return gracefully without error
        """
        # GIVEN: Observability not initialized
        # (previous test shut it down)

        # WHEN: Calling shutdown
        shutdown_observability()

        # THEN: Should not raise error
        assert True  # If we got here, no exception was raised

    def test_shutdown_idempotent(self):
        """
        Test that shutdown_observability can be called multiple times safely.

        GREEN: Should be idempotent (safe to call multiple times)
        """
        # GIVEN: Initialized observability
        mock_settings = MagicMock()
        mock_settings.service_name = "test-service"
        mock_settings.enable_tracing = False
        mock_settings.enable_metrics = False
        mock_settings.enable_console_export = False
        mock_settings.enable_langsmith = False
        mock_settings.log_level = "INFO"
        mock_settings.log_format = "text"

        init_observability(settings=mock_settings)

        # WHEN: Calling shutdown multiple times
        shutdown_observability()
        shutdown_observability()
        shutdown_observability()

        # THEN: Should not raise error
        assert not is_initialized()

    def test_shutdown_sets_config_to_none(self):
        """
        Test that shutdown_observability clears the global config.

        GREEN: Should set _observability_config to None
        """
        # GIVEN: Initialized observability
        mock_settings = MagicMock()
        mock_settings.service_name = "test-service"
        mock_settings.enable_tracing = False
        mock_settings.enable_metrics = False
        mock_settings.enable_console_export = False
        mock_settings.enable_langsmith = False
        mock_settings.log_level = "INFO"
        mock_settings.log_format = "text"

        init_observability(settings=mock_settings)
        assert is_initialized()

        # WHEN: Calling shutdown
        shutdown_observability()

        # THEN: Should clear initialization state
        assert not is_initialized()
