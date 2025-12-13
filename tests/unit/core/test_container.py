"""Tests for DI container protocols (ISP compliance)."""

import gc
import logging

import pytest

from mcp_server_langgraph.core.container import (
    LoggerProvider,
    MetricsProvider,
    NoOpLogger,
    NoOpMetrics,
    NoOpTelemetryProvider,
    NoOpTracer,
    TelemetryProvider,
    TracerProvider,
)

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="test_container")
class TestGranularProtocols:
    """Tests for granular telemetry protocols (ISP fix)."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_logger_provider_protocol_exists(self) -> None:
        """LoggerProvider protocol should be defined."""
        assert hasattr(LoggerProvider, "__protocol_attrs__") or hasattr(LoggerProvider, "logger")

    def test_metrics_provider_protocol_exists(self) -> None:
        """MetricsProvider protocol should be defined."""
        assert hasattr(MetricsProvider, "__protocol_attrs__") or hasattr(MetricsProvider, "metrics")

    def test_tracer_provider_protocol_exists(self) -> None:
        """TracerProvider protocol should be defined."""
        assert hasattr(TracerProvider, "__protocol_attrs__") or hasattr(TracerProvider, "tracer")


@pytest.mark.xdist_group(name="test_container")
class TestLoggerOnlyProvider:
    """Test that we can create a provider with only logger."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_logger_only_class_is_valid_logger_provider(self) -> None:
        """A class with only logger should satisfy LoggerProvider."""

        class LoggerOnlyImpl:
            @property
            def logger(self) -> logging.Logger:
                return logging.getLogger("test")

        impl = LoggerOnlyImpl()
        assert isinstance(impl, LoggerProvider)

    def test_logger_only_class_is_not_full_telemetry_provider(self) -> None:
        """A class with only logger should NOT satisfy TelemetryProvider."""

        class LoggerOnlyImpl:
            @property
            def logger(self) -> logging.Logger:
                return logging.getLogger("test")

        impl = LoggerOnlyImpl()
        # Should NOT be a full TelemetryProvider
        assert not isinstance(impl, TelemetryProvider)


@pytest.mark.xdist_group(name="test_container")
class TestNoOpProviders:
    """Tests for no-op implementations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_noop_logger_has_all_log_methods(self) -> None:
        """NoOpLogger should have info, debug, warning, error, critical."""
        logger = NoOpLogger()
        assert hasattr(logger, "info")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "critical")

    def test_noop_metrics_has_counter_gauge_histogram(self) -> None:
        """NoOpMetrics should have counter, gauge, histogram."""
        metrics = NoOpMetrics()
        assert hasattr(metrics, "counter")
        assert hasattr(metrics, "gauge")
        assert hasattr(metrics, "histogram")

    def test_noop_tracer_has_start_as_current_span(self) -> None:
        """NoOpTracer should have start_as_current_span."""
        tracer = NoOpTracer()
        assert hasattr(tracer, "start_as_current_span")


@pytest.mark.xdist_group(name="test_container")
class TestTelemetryProviderComposite:
    """Tests for composite TelemetryProvider."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_noop_telemetry_is_logger_provider(self) -> None:
        """NoOpTelemetryProvider should be a LoggerProvider."""
        provider = NoOpTelemetryProvider()
        assert isinstance(provider, LoggerProvider)

    def test_noop_telemetry_is_metrics_provider(self) -> None:
        """NoOpTelemetryProvider should be a MetricsProvider."""
        provider = NoOpTelemetryProvider()
        assert isinstance(provider, MetricsProvider)

    def test_noop_telemetry_is_tracer_provider(self) -> None:
        """NoOpTelemetryProvider should be a TracerProvider."""
        provider = NoOpTelemetryProvider()
        assert isinstance(provider, TracerProvider)

    def test_noop_telemetry_is_full_telemetry_provider(self) -> None:
        """NoOpTelemetryProvider should satisfy full TelemetryProvider."""
        provider = NoOpTelemetryProvider()
        assert isinstance(provider, TelemetryProvider)
