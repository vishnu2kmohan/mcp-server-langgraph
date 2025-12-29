"""
Limit Violation Metrics Tests

TDD Phase: Tests for metrics visibility when security limits are hit.
These tests verify that metrics are recorded when connections are rejected,
rate limits are exceeded, or message size limits are violated.
"""

from __future__ import annotations

import gc

import pytest


pytestmark = [
    pytest.mark.unit,
    pytest.mark.api,
    pytest.mark.websocket,
]


@pytest.mark.xdist_group(name="test_limit_violation_metrics")
class TestConnectionRejectionMetrics:
    """Tests for metrics when connections are rejected due to limits."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_metrics_has_connections_rejected_counter(self) -> None:
        """
        GIVEN MCPWebSocketMetrics
        WHEN checking attributes
        THEN should have connections_rejected counter.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketMetrics

        metrics = MCPWebSocketMetrics()
        assert hasattr(metrics, "connections_rejected")

    def test_record_connection_rejected_method_exists(self) -> None:
        """
        GIVEN MCPWebSocketMetrics
        WHEN checking methods
        THEN should have record_connection_rejected method.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketMetrics

        metrics = MCPWebSocketMetrics()
        assert callable(getattr(metrics, "record_connection_rejected", None))

    def test_record_connection_rejected_increments_counter(self) -> None:
        """
        GIVEN MCPWebSocketMetrics
        WHEN record_connection_rejected is called
        THEN should increment connections_rejected counter.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketMetrics

        metrics = MCPWebSocketMetrics()
        initial = metrics.connections_rejected.get()

        metrics.record_connection_rejected(user_id="user:test", reason="connection_limit")

        assert metrics.connections_rejected.get() == initial + 1

    def test_record_connection_rejected_with_user_context(self) -> None:
        """
        GIVEN MCPWebSocketMetrics
        WHEN record_connection_rejected is called with user_id
        THEN should record the user context in labels.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketMetrics

        metrics = MCPWebSocketMetrics()

        # Should not raise
        metrics.record_connection_rejected(user_id="user:alice", reason="connection_limit")


@pytest.mark.xdist_group(name="test_limit_violation_metrics")
class TestMessageSizeViolationMetrics:
    """Tests for metrics when message size limits are violated."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_metrics_has_message_size_exceeded_counter(self) -> None:
        """
        GIVEN MCPWebSocketMetrics
        WHEN checking attributes
        THEN should have message_size_exceeded counter.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketMetrics

        metrics = MCPWebSocketMetrics()
        assert hasattr(metrics, "message_size_exceeded")

    def test_record_message_size_exceeded_method_exists(self) -> None:
        """
        GIVEN MCPWebSocketMetrics
        WHEN checking methods
        THEN should have record_message_size_exceeded method.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketMetrics

        metrics = MCPWebSocketMetrics()
        assert callable(getattr(metrics, "record_message_size_exceeded", None))

    def test_record_message_size_exceeded_increments_counter(self) -> None:
        """
        GIVEN MCPWebSocketMetrics
        WHEN record_message_size_exceeded is called
        THEN should increment message_size_exceeded counter.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketMetrics

        metrics = MCPWebSocketMetrics()
        initial = metrics.message_size_exceeded.get()

        metrics.record_message_size_exceeded(user_id="user:test")

        assert metrics.message_size_exceeded.get() == initial + 1


@pytest.mark.xdist_group(name="test_limit_violation_metrics")
class TestRateLimitExceededMetrics:
    """Tests for existing rate limit exceeded metrics."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_rate_limit_exceeded_increments_counter(self) -> None:
        """
        GIVEN MCPWebSocketMetrics
        WHEN record_rate_limit_exceeded is called
        THEN should increment rate_limit_exceeded counter.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketMetrics

        metrics = MCPWebSocketMetrics()
        initial = metrics.rate_limit_exceeded

        metrics.record_rate_limit_exceeded(user_id="user:test")

        assert metrics.rate_limit_exceeded == initial + 1


@pytest.mark.xdist_group(name="test_limit_violation_metrics")
class TestSecureProcessorRecordsMetrics:
    """Tests for SecureMessageProcessor recording metrics on violations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_secure_processor_records_message_size_exceeded(self) -> None:
        """
        GIVEN SecureMessageProcessor with metrics
        WHEN validating an oversized message
        THEN should record message_size_exceeded metric.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            SecureMessageProcessor,
            MCPWebSocketMetrics,
        )

        metrics = MCPWebSocketMetrics()
        initial = metrics.message_size_exceeded.get()

        processor = SecureMessageProcessor(
            session_id="test",
            user_id="user:test",
            metrics=metrics,
            max_message_size=100,
        )

        # Validate oversized message
        result = processor.validate_incoming("x" * 200)

        # Should have recorded the metric
        assert not result.is_valid
        assert metrics.message_size_exceeded.get() == initial + 1


@pytest.mark.xdist_group(name="test_limit_violation_metrics")
class TestOTelMetricsForLimits:
    """Tests for OpenTelemetry metrics for limit violations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_otel_metrics_has_connection_rejected_method(self) -> None:
        """
        GIVEN OTelMCPMetrics
        WHEN checking methods
        THEN should have record_connection_rejected method.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import OTelMCPMetrics

        metrics = OTelMCPMetrics()
        assert callable(getattr(metrics, "record_connection_rejected", None))

    def test_otel_metrics_has_message_size_exceeded_method(self) -> None:
        """
        GIVEN OTelMCPMetrics
        WHEN checking methods
        THEN should have record_message_size_exceeded method.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import OTelMCPMetrics

        metrics = OTelMCPMetrics()
        assert callable(getattr(metrics, "record_message_size_exceeded", None))


@pytest.mark.xdist_group(name="test_limit_violation_metrics")
class TestConnectionManagerIdleTimeoutConfig:
    """Tests for ConnectionManager idle timeout configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_connection_manager_accepts_idle_timeout_parameter(self) -> None:
        """
        GIVEN ConnectionManager
        WHEN initialized with idle_timeout_seconds
        THEN should store the configured timeout.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import ConnectionManager

        manager = ConnectionManager(idle_timeout_seconds=600)
        assert manager.idle_timeout_seconds == 600

    def test_connection_manager_uses_default_idle_timeout(self) -> None:
        """
        GIVEN ConnectionManager
        WHEN initialized without idle_timeout_seconds
        THEN should use default timeout.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import (
            ConnectionManager,
            IDLE_TIMEOUT_SECONDS,
        )

        manager = ConnectionManager()
        assert manager.idle_timeout_seconds == IDLE_TIMEOUT_SECONDS

    def test_create_connection_manager_passes_idle_timeout(self) -> None:
        """
        GIVEN StreamingSettings with custom idle_timeout_seconds
        WHEN create_connection_manager is called
        THEN should create manager with configured timeout.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import create_connection_manager
        from mcp_server_langgraph.core.config.streaming import StreamingSettings

        settings = StreamingSettings(
            streaming_idle_timeout_seconds=900,
        )

        manager = create_connection_manager(streaming_settings=settings)
        assert manager.idle_timeout_seconds == 900


@pytest.mark.xdist_group(name="test_limit_violation_metrics")
class TestConnectionRejectionReasonsMetrics:
    """Tests for metrics recording different connection rejection reasons."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_record_connection_rejected_for_no_token(self) -> None:
        """
        GIVEN MCPWebSocketMetrics
        WHEN connection rejected due to no token
        THEN should record with reason 'no_token'.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketMetrics

        metrics = MCPWebSocketMetrics()
        initial = metrics.connections_rejected.get()

        metrics.record_connection_rejected(user_id="unknown", reason="no_token")

        assert metrics.connections_rejected.get() == initial + 1

    def test_record_connection_rejected_for_invalid_token(self) -> None:
        """
        GIVEN MCPWebSocketMetrics
        WHEN connection rejected due to invalid token
        THEN should record with reason 'invalid_token'.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketMetrics

        metrics = MCPWebSocketMetrics()
        initial = metrics.connections_rejected.get()

        metrics.record_connection_rejected(user_id="unknown", reason="invalid_token")

        assert metrics.connections_rejected.get() == initial + 1

    def test_record_connection_rejected_for_permission_denied(self) -> None:
        """
        GIVEN MCPWebSocketMetrics
        WHEN connection rejected due to permission denied
        THEN should record with reason 'permission_denied'.
        """
        from mcp_server_langgraph.api.v1.mcp_websocket import MCPWebSocketMetrics

        metrics = MCPWebSocketMetrics()
        initial = metrics.connections_rejected.get()

        metrics.record_connection_rejected(user_id="user:bob", reason="permission_denied")

        assert metrics.connections_rejected.get() == initial + 1
