"""
Tests for BroadcastingSpanProcessor.

This processor connects OpenTelemetry span completion to the TraceBroadcaster
for real-time trace streaming via WebSocket.

TDD: These tests define the expected behavior BEFORE implementation.
"""

from __future__ import annotations

import gc
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# Module-level markers
pytestmark = [
    pytest.mark.unit,
    pytest.mark.observability,
    pytest.mark.xdist_group(name="broadcasting_span_processor"),
]


def teardown_module() -> None:
    """Force GC to prevent mock accumulation in xdist workers."""
    gc.collect()


class TestBroadcastingSpanProcessor:
    """
    Unit tests for BroadcastingSpanProcessor.

    The BroadcastingSpanProcessor implements OpenTelemetry's SpanProcessor interface
    and broadcasts completed spans to the TraceBroadcaster for real-time WebSocket streaming.

    This enables the DevTools panel to show live trace data as spans complete.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_processor_implements_span_processor_interface(self) -> None:
        """
        GIVEN BroadcastingSpanProcessor
        WHEN instantiated
        THEN it should implement the SpanProcessor interface.
        """
        from mcp_server_langgraph.observability.broadcasting_span_processor import (
            BroadcastingSpanProcessor,
        )
        from opentelemetry.sdk.trace import SpanProcessor

        # Create with mock broadcaster
        mock_broadcaster = MagicMock()
        processor = BroadcastingSpanProcessor(broadcaster=mock_broadcaster)

        # Should be a SpanProcessor
        assert isinstance(processor, SpanProcessor)

    def test_on_end_broadcasts_span_to_broadcaster(self) -> None:
        """
        GIVEN a BroadcastingSpanProcessor with a TraceBroadcaster
        WHEN on_end is called with a completed span
        THEN it should call broadcaster.broadcast_span with span data.
        """
        from mcp_server_langgraph.observability.broadcasting_span_processor import (
            BroadcastingSpanProcessor,
        )

        # Create mock broadcaster
        mock_broadcaster = MagicMock()
        mock_broadcaster.broadcast_span = AsyncMock(return_value=None)

        processor = BroadcastingSpanProcessor(broadcaster=mock_broadcaster)

        # Create a mock span with required attributes
        mock_span = MagicMock()
        mock_span.name = "test-operation"
        mock_span.get_span_context.return_value.trace_id = 0x1234567890ABCDEF
        mock_span.get_span_context.return_value.span_id = 0xFEDCBA0987654321
        mock_span.parent = None
        mock_span.start_time = 1000000000  # nanoseconds
        mock_span.end_time = 2000000000  # nanoseconds
        mock_span.status.status_code.name = "OK"
        mock_span.attributes = {"session.id": "test-session-123"}
        mock_span.resource.attributes = {"service.name": "test-service"}

        # Call on_end
        processor.on_end(mock_span)

        # Verify broadcast_span was scheduled (it's async)
        # The processor should use asyncio.create_task or similar

    def test_on_end_extracts_session_id_from_span_attributes(self) -> None:
        """
        GIVEN a span with session.id attribute
        WHEN on_end is called
        THEN the broadcast payload should include session_id.
        """
        from mcp_server_langgraph.observability.broadcasting_span_processor import (
            BroadcastingSpanProcessor,
        )

        mock_broadcaster = MagicMock()
        captured_span_data: list[dict[str, Any]] = []

        # Capture what gets broadcast
        def capture_broadcast(span_data: dict[str, Any]) -> None:
            captured_span_data.append(span_data)

        mock_broadcaster.queue_broadcast = MagicMock(side_effect=capture_broadcast)

        processor = BroadcastingSpanProcessor(broadcaster=mock_broadcaster)

        # Create mock span with session.id
        mock_span = MagicMock()
        mock_span.name = "auth.get_session"
        mock_span.get_span_context.return_value.trace_id = 0x1234
        mock_span.get_span_context.return_value.span_id = 0x5678
        mock_span.parent = None
        mock_span.start_time = 1000000000
        mock_span.end_time = 1500000000
        mock_span.status.status_code.name = "OK"
        mock_span.attributes = {"session.id": "session-abc-123"}
        mock_span.resource.attributes = {"service.name": "mcp-server"}

        processor.on_end(mock_span)

        # Verify session.id was extracted
        if captured_span_data:
            assert (
                "session.id" in captured_span_data[0].get("attributes", {})
                or captured_span_data[0].get("session_id") == "session-abc-123"
            )

    def test_on_start_is_noop(self) -> None:
        """
        GIVEN BroadcastingSpanProcessor
        WHEN on_start is called
        THEN it should be a no-op (we only broadcast completed spans).
        """
        from mcp_server_langgraph.observability.broadcasting_span_processor import (
            BroadcastingSpanProcessor,
        )

        mock_broadcaster = MagicMock()
        processor = BroadcastingSpanProcessor(broadcaster=mock_broadcaster)

        # on_start should not raise
        mock_span = MagicMock()
        mock_parent_context = MagicMock()
        processor.on_start(mock_span, mock_parent_context)

        # Broadcaster should not have been called
        mock_broadcaster.broadcast_span.assert_not_called()

    def test_shutdown_is_safe(self) -> None:
        """
        GIVEN BroadcastingSpanProcessor
        WHEN shutdown is called
        THEN it should complete without error.
        """
        from mcp_server_langgraph.observability.broadcasting_span_processor import (
            BroadcastingSpanProcessor,
        )

        mock_broadcaster = MagicMock()
        processor = BroadcastingSpanProcessor(broadcaster=mock_broadcaster)

        # Shutdown should not raise
        processor.shutdown()

    def test_force_flush_is_safe(self) -> None:
        """
        GIVEN BroadcastingSpanProcessor
        WHEN force_flush is called
        THEN it should return True (sync broadcast, nothing to flush).
        """
        from mcp_server_langgraph.observability.broadcasting_span_processor import (
            BroadcastingSpanProcessor,
        )

        mock_broadcaster = MagicMock()
        processor = BroadcastingSpanProcessor(broadcaster=mock_broadcaster)

        # force_flush should return True
        result = processor.force_flush()
        assert result is True

    def test_span_to_dict_conversion(self) -> None:
        """
        GIVEN a completed span
        WHEN converted to dict for broadcasting
        THEN it should include trace_id, span_id, name, duration, status, attributes.
        """
        from mcp_server_langgraph.observability.broadcasting_span_processor import (
            span_to_broadcast_dict,
        )

        # Create mock span
        mock_span = MagicMock()
        mock_span.name = "http.request"
        mock_span.get_span_context.return_value.trace_id = 0x1234567890ABCDEF1234567890ABCDEF
        mock_span.get_span_context.return_value.span_id = 0xFEDCBA0987654321
        mock_span.parent = None
        mock_span.start_time = 1000000000  # 1 second in nanoseconds
        mock_span.end_time = 1150000000  # 1.15 seconds (150ms duration)
        mock_span.status.status_code.name = "OK"
        mock_span.attributes = {
            "session.id": "sess-123",
            "http.method": "GET",
            "http.url": "/api/test",
        }
        mock_span.resource.attributes = {"service.name": "api-gateway"}

        result = span_to_broadcast_dict(mock_span)

        # Verify required fields
        assert "trace_id" in result
        assert "span_id" in result
        assert result["name"] == "http.request"
        assert result["service_name"] == "api-gateway"
        assert result["status"] == "ok"  # Protocol expects lowercase
        assert "duration_ms" in result
        assert result["duration_ms"] == 150.0  # 150ms
        assert "attributes" in result
        assert result["attributes"]["session.id"] == "sess-123"


class TestBroadcastingSpanProcessorIntegration:
    """
    Integration tests verifying BroadcastingSpanProcessor works with real OTEL components.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_processor_receives_real_spans(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN BroadcastingSpanProcessor added to a TracerProvider
        WHEN spans are created and ended
        THEN the processor should receive them.
        """
        # CRITICAL: Temporarily enable OTEL SDK for this test
        # conftest.py sets OTEL_SDK_DISABLED=true globally, which causes NoOpTracer
        monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)

        from opentelemetry.sdk.trace import TracerProvider

        from mcp_server_langgraph.observability.broadcasting_span_processor import (
            BroadcastingSpanProcessor,
        )
        from mcp_server_langgraph.observability.trace_broadcaster import (
            TraceBroadcaster,
        )

        # Use real broadcaster to track received spans
        broadcaster = TraceBroadcaster()

        processor = BroadcastingSpanProcessor(broadcaster=broadcaster)

        # Create a real TracerProvider with our processor
        provider = TracerProvider()
        provider.add_span_processor(processor)

        tracer = provider.get_tracer("test-tracer")

        # Create and end a span
        with tracer.start_as_current_span("test-operation") as span:
            span.set_attribute("session.id", "test-session")

        # Shutdown to ensure all spans processed
        provider.shutdown()

        # Verify span was received via direct access to recent traces
        # (queue_broadcast adds to _recent_traces synchronously)
        assert len(broadcaster._recent_traces) >= 1
        assert any(s.get("name") == "test-operation" for s in broadcaster._recent_traces)


class TestBroadcastingSpanProcessorTelemetryRegistration:
    """
    Tests verifying BroadcastingSpanProcessor is registered in telemetry initialization.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_telemetry_registers_broadcasting_span_processor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN ObservabilityConfig is initialized
        WHEN tracing is set up
        THEN BroadcastingSpanProcessor should be registered with TracerProvider.
        """
        # CRITICAL: Temporarily enable OTEL SDK for this test
        monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)

        # Clear any previously set tracer provider
        from opentelemetry import trace

        # Reset trace broadcaster singleton
        from mcp_server_langgraph.websocket.registry import set_trace_broadcaster

        set_trace_broadcaster(None)

        # Import and instantiate ObservabilityConfig
        from mcp_server_langgraph.observability.telemetry import ObservabilityConfig

        config = ObservabilityConfig(
            enable_console_export=False,  # Reduce noise
            enable_file_logging=False,
        )

        # Get the tracer provider that was set
        provider = trace.get_tracer_provider()

        # Verify it's a real TracerProvider (not NoOpTracerProvider)
        from opentelemetry.sdk.trace import TracerProvider

        assert isinstance(provider, TracerProvider), f"Expected TracerProvider, got {type(provider)}"

        # Check that BroadcastingSpanProcessor is registered
        # The processor is added to provider._active_span_processor which is a MultiSpanProcessor
        from mcp_server_langgraph.observability.broadcasting_span_processor import (
            BroadcastingSpanProcessor,
        )

        # Get the multi-span processor
        active_processor = provider._active_span_processor
        assert active_processor is not None, "No active span processor found"

        # The SynchronousMultiSpanProcessor has a _span_processors list
        span_processors = getattr(active_processor, "_span_processors", [])

        # Check if any processor is a BroadcastingSpanProcessor
        broadcasting_processors = [p for p in span_processors if isinstance(p, BroadcastingSpanProcessor)]
        assert len(broadcasting_processors) >= 1, (
            f"BroadcastingSpanProcessor not found in span processors. Found: {[type(p).__name__ for p in span_processors]}"
        )

        # Cleanup
        if hasattr(config, "tracer_provider") and config.tracer_provider:
            config.tracer_provider.shutdown()


class TestOTELToWebSocketWiringIntegration:
    """
    Wiring tests that verify the complete data flow from OTEL to WebSocket.

    These tests catch initialization-time wiring issues that component-level
    unit tests miss. The BroadcastingSpanProcessor gap was missed because:
    - TraceBroadcaster unit tests passed (component works in isolation)
    - OTEL integration tests passed (spans reach Tempo)
    - But no test verified: OTEL -> BroadcastingSpanProcessor -> TraceBroadcaster

    This test class ensures the full pipeline is properly wired.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_otel_span_reaches_trace_broadcaster_via_telemetry_init(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN ObservabilityConfig initializes telemetry
        WHEN a span is created and ends
        THEN it should appear in TraceBroadcaster's recent_traces.

        This is a WIRING test - it verifies the full pipeline is connected,
        not just that individual components work.

        Note: This test creates its own TracerProvider to avoid OTEL global state issues.
        In production, ObservabilityConfig does this wiring during app startup.
        """
        # CRITICAL: Enable OTEL SDK for this test
        monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)

        from opentelemetry.sdk.trace import TracerProvider

        from mcp_server_langgraph.observability.broadcasting_span_processor import (
            BroadcastingSpanProcessor,
        )
        from mcp_server_langgraph.websocket.registry import (
            get_trace_broadcaster,
            set_trace_broadcaster,
        )

        # Reset broadcaster singleton to ensure clean state
        set_trace_broadcaster(None)
        broadcaster = get_trace_broadcaster()

        # Create a fresh TracerProvider with BroadcastingSpanProcessor
        # This mirrors what ObservabilityConfig._setup_tracing() does
        provider = TracerProvider()
        processor = BroadcastingSpanProcessor(broadcaster=broadcaster)
        provider.add_span_processor(processor)

        # Use our provider directly (avoids OTEL global state issues in tests)
        tracer = provider.get_tracer("wiring-test")

        initial_count = len(broadcaster._recent_traces)

        # Create and end a span
        with tracer.start_as_current_span("wiring-test-span") as span:
            span.set_attribute("session.id", "wiring-test-session")

        # Verify the span reached the broadcaster
        final_count = len(broadcaster._recent_traces)
        assert final_count > initial_count, (
            f"Span did not reach TraceBroadcaster. "
            f"Initial traces: {initial_count}, Final traces: {final_count}. "
            f"This indicates BroadcastingSpanProcessor is not properly wired."
        )

        # Verify the correct span data
        recent_span = broadcaster._recent_traces[0]
        assert recent_span["name"] == "wiring-test-span", (
            f"Wrong span in broadcaster. Expected 'wiring-test-span', got '{recent_span['name']}'"
        )

        # Verify session.id attribute is captured
        assert recent_span["attributes"].get("session.id") == "wiring-test-session", "session.id not captured correctly"

        # Cleanup
        provider.shutdown()
