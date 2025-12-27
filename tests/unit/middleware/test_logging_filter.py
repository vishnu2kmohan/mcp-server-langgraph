"""
Unit tests for QuietPathsLoggingFilter middleware.

TDD: These tests define expected behavior for the QUIET_LOGS log filtering middleware.
The filter should:
- Allow all logs when QUIET_LOGS=false (default)
- Suppress health check endpoint logs when QUIET_LOGS=true
- Suppress metrics endpoint logs when QUIET_LOGS=true
- Suppress static asset logs when QUIET_LOGS=true
- Allow API request logs when QUIET_LOGS=true
"""

import gc
import logging

import pytest

# Mark all tests in this module as unit tests
pytestmark = pytest.mark.unit


@pytest.fixture
def quiet_logs_enabled(monkeypatch):
    """Enable QUIET_LOGS environment variable."""
    monkeypatch.setenv("QUIET_LOGS", "true")


@pytest.fixture
def quiet_logs_disabled(monkeypatch):
    """Disable QUIET_LOGS environment variable."""
    monkeypatch.setenv("QUIET_LOGS", "false")


@pytest.fixture
def log_record_factory():
    """Factory to create log records with different messages."""

    def _create(message: str) -> logging.LogRecord:
        record = logging.LogRecord(
            name="uvicorn.access",
            level=logging.INFO,
            pathname="/app/uvicorn/access.py",
            lineno=42,
            msg=message,
            args=(),
            exc_info=None,
            func="log_access",
        )
        return record

    return _create


@pytest.mark.xdist_group(name="logging_filter")
class TestQuietPathsLoggingFilter:
    """Tests for QuietPathsLoggingFilter class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_filter_allows_all_logs_when_quiet_disabled(self, quiet_logs_disabled, log_record_factory) -> None:
        """Test that all logs are allowed when QUIET_LOGS=false."""
        from mcp_server_langgraph.middleware.logging_filter import (
            QuietPathsLoggingFilter,
        )

        log_filter = QuietPathsLoggingFilter()

        # All paths should be allowed
        health_record = log_record_factory('GET /health HTTP/1.1" 200')
        metrics_record = log_record_factory('GET /metrics HTTP/1.1" 200')
        api_record = log_record_factory('POST /api/v1/agents HTTP/1.1" 201')
        static_record = log_record_factory('GET /studio/assets/main.js HTTP/1.1" 200')

        assert log_filter.filter(health_record) is True
        assert log_filter.filter(metrics_record) is True
        assert log_filter.filter(api_record) is True
        assert log_filter.filter(static_record) is True

    def test_filter_suppresses_health_endpoints_when_quiet_enabled(self, quiet_logs_enabled, log_record_factory) -> None:
        """Test that health check endpoint logs are suppressed when QUIET_LOGS=true."""
        from mcp_server_langgraph.middleware.logging_filter import (
            QuietPathsLoggingFilter,
        )

        log_filter = QuietPathsLoggingFilter()

        # Health endpoints should be suppressed
        assert log_filter.filter(log_record_factory('GET /health HTTP/1.1" 200')) is False
        assert log_filter.filter(log_record_factory('GET /healthz HTTP/1.1" 200')) is False
        assert log_filter.filter(log_record_factory('GET /health/live HTTP/1.1" 200')) is False
        assert log_filter.filter(log_record_factory('GET /health/ready HTTP/1.1" 200')) is False
        assert log_filter.filter(log_record_factory('GET /ready HTTP/1.1" 200')) is False
        assert log_filter.filter(log_record_factory('GET /readyz HTTP/1.1" 200')) is False
        assert log_filter.filter(log_record_factory('GET /livez HTTP/1.1" 200')) is False

    def test_filter_suppresses_metrics_endpoint_when_quiet_enabled(self, quiet_logs_enabled, log_record_factory) -> None:
        """Test that metrics endpoint logs are suppressed when QUIET_LOGS=true."""
        from mcp_server_langgraph.middleware.logging_filter import (
            QuietPathsLoggingFilter,
        )

        log_filter = QuietPathsLoggingFilter()

        # Metrics endpoint should be suppressed
        assert log_filter.filter(log_record_factory('GET /metrics HTTP/1.1" 200')) is False
        # Metrics subpaths should also be suppressed
        assert log_filter.filter(log_record_factory('GET /metrics/prometheus HTTP/1.1" 200')) is False

    def test_filter_suppresses_static_assets_when_quiet_enabled(self, quiet_logs_enabled, log_record_factory) -> None:
        """Test that static asset logs are suppressed when QUIET_LOGS=true."""
        from mcp_server_langgraph.middleware.logging_filter import (
            QuietPathsLoggingFilter,
        )

        log_filter = QuietPathsLoggingFilter()

        # Static assets should be suppressed
        assert log_filter.filter(log_record_factory('GET /studio/assets/main.js HTTP/1.1" 200')) is False
        assert log_filter.filter(log_record_factory('GET /static/styles.css HTTP/1.1" 200')) is False
        assert log_filter.filter(log_record_factory('GET /fonts/roboto.woff2 HTTP/1.1" 200')) is False
        assert log_filter.filter(log_record_factory('GET /sounds/notification.mp3 HTTP/1.1" 200')) is False
        assert log_filter.filter(log_record_factory('GET /favicon.ico HTTP/1.1" 200')) is False

    def test_filter_suppresses_service_worker_files_when_quiet_enabled(self, quiet_logs_enabled, log_record_factory) -> None:
        """Test that service worker files are suppressed when QUIET_LOGS=true."""
        from mcp_server_langgraph.middleware.logging_filter import (
            QuietPathsLoggingFilter,
        )

        log_filter = QuietPathsLoggingFilter()

        # Service worker files should be suppressed
        assert log_filter.filter(log_record_factory('GET /studio/sw.js HTTP/1.1" 200')) is False
        assert log_filter.filter(log_record_factory('GET /studio/workbox-abc123.js HTTP/1.1" 200')) is False

    def test_filter_allows_api_requests_when_quiet_enabled(self, quiet_logs_enabled, log_record_factory) -> None:
        """Test that API request logs are allowed when QUIET_LOGS=true."""
        from mcp_server_langgraph.middleware.logging_filter import (
            QuietPathsLoggingFilter,
        )

        log_filter = QuietPathsLoggingFilter()

        # API requests should be allowed
        assert log_filter.filter(log_record_factory('POST /api/v1/agents HTTP/1.1" 201')) is True
        assert log_filter.filter(log_record_factory('GET /api/v1/sessions HTTP/1.1" 200')) is True
        assert log_filter.filter(log_record_factory('POST /api/v1/chat/completions HTTP/1.1" 200')) is True
        # Studio pages (not assets) should be allowed
        assert log_filter.filter(log_record_factory('GET /studio HTTP/1.1" 200')) is True
        assert log_filter.filter(log_record_factory('GET /studio/canvas HTTP/1.1" 200')) is True

    def test_filter_handles_various_log_formats(self, quiet_logs_enabled, log_record_factory) -> None:
        """Test that filter handles different log message formats."""
        from mcp_server_langgraph.middleware.logging_filter import (
            QuietPathsLoggingFilter,
        )

        log_filter = QuietPathsLoggingFilter()

        # Uvicorn format: '127.0.0.1:8000 - "GET /health HTTP/1.1" 200'
        assert log_filter.filter(log_record_factory('127.0.0.1:8000 - "GET /health HTTP/1.1" 200')) is False

        # Traefik JSON format: {"RequestPath":"/health",...}
        assert log_filter.filter(log_record_factory('{"RequestPath":"/health","status":200}')) is False

        # Generic format with path
        assert log_filter.filter(log_record_factory("Request to /health completed")) is False

    def test_quiet_logs_enabled_property(self, quiet_logs_enabled) -> None:
        """Test that quiet_logs_enabled property reflects environment variable."""
        from mcp_server_langgraph.middleware.logging_filter import (
            QuietPathsLoggingFilter,
        )

        log_filter = QuietPathsLoggingFilter()
        assert log_filter.quiet_logs_enabled is True

    def test_quiet_logs_disabled_property(self, quiet_logs_disabled) -> None:
        """Test that quiet_logs_enabled property reflects environment variable."""
        from mcp_server_langgraph.middleware.logging_filter import (
            QuietPathsLoggingFilter,
        )

        log_filter = QuietPathsLoggingFilter()
        assert log_filter.quiet_logs_enabled is False

    def test_filter_handles_malformed_log_records(self, quiet_logs_enabled) -> None:
        """Test that filter handles malformed log records gracefully."""
        from mcp_server_langgraph.middleware.logging_filter import (
            QuietPathsLoggingFilter,
        )

        log_filter = QuietPathsLoggingFilter()

        # Create a record that raises on getMessage()
        class BrokenRecord(logging.LogRecord):
            def getMessage(self):
                raise RuntimeError("Broken record")

        broken_record = BrokenRecord(
            name="test",
            level=logging.INFO,
            pathname="/test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None,
        )

        # Should return True (allow) on error
        assert log_filter.filter(broken_record) is True


@pytest.mark.xdist_group(name="logging_filter")
class TestSetupQuietLogging:
    """Tests for setup_quiet_logging function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_setup_applies_filter_to_uvicorn_access_logger(self, quiet_logs_enabled) -> None:
        """Test that setup_quiet_logging applies filter to uvicorn.access logger."""
        from mcp_server_langgraph.middleware.logging_filter import (
            QuietPathsLoggingFilter,
            setup_quiet_logging,
        )

        # Clear existing filters
        uvicorn_logger = logging.getLogger("uvicorn.access")
        uvicorn_logger.filters = []

        setup_quiet_logging()

        # Check filter was added
        assert any(isinstance(f, QuietPathsLoggingFilter) for f in uvicorn_logger.filters)

    def test_setup_does_not_add_duplicate_filters(self, quiet_logs_enabled) -> None:
        """Test that setup_quiet_logging doesn't add duplicate filters."""
        from mcp_server_langgraph.middleware.logging_filter import (
            QuietPathsLoggingFilter,
            setup_quiet_logging,
        )

        # Clear existing filters
        uvicorn_logger = logging.getLogger("uvicorn.access")
        uvicorn_logger.filters = []

        # Call setup twice
        setup_quiet_logging()
        setup_quiet_logging()

        # Should only have one filter
        filter_count = sum(1 for f in uvicorn_logger.filters if isinstance(f, QuietPathsLoggingFilter))
        assert filter_count == 1

    def test_setup_does_nothing_when_quiet_disabled(self, quiet_logs_disabled) -> None:
        """Test that setup_quiet_logging does nothing when QUIET_LOGS=false."""
        from mcp_server_langgraph.middleware.logging_filter import (
            QuietPathsLoggingFilter,
            setup_quiet_logging,
        )

        # Clear existing filters
        uvicorn_logger = logging.getLogger("uvicorn.access")
        uvicorn_logger.filters = []

        setup_quiet_logging()

        # No filter should be added
        assert not any(isinstance(f, QuietPathsLoggingFilter) for f in uvicorn_logger.filters)
