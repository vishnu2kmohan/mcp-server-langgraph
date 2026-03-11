"""
Integration tests for DevTools trace emission with session.id propagation.

These tests verify that the SessionPropagatingSpanProcessor is correctly
integrated into the observability stack for DevTools trace visualization.

Triple-AI Review: This test suite was added to address finding #6 from the
Claude + Codex + Gemini review of the trace rendering fix plan.

Note: Due to OpenTelemetry's global singleton pattern, full end-to-end span
creation tests require the test infrastructure (docker-compose.test.yml).
These tests focus on verifiable integration points.

See: ~/.claude/plans/lucky-juggling-flamingo.md
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    pass

# Module-level markers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.observability,
    pytest.mark.xdist_group(name="devtools_trace_emission"),
]


def teardown_module() -> None:
    """Force GC to prevent mock accumulation in xdist workers."""
    gc.collect()


@pytest.mark.xdist_group("test_session_propagating_span_processor_integration")
class TestSessionPropagatingSpanProcessorIntegration:
    """
    Integration tests for SessionPropagatingSpanProcessor in the observability stack.

    These tests verify that the processor is correctly integrated and exported.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_processor_exported_from_observability_module(self) -> None:
        """
        GIVEN the observability module
        WHEN importing SessionPropagatingSpanProcessor
        THEN it should be available as an export.
        """
        from mcp_server_langgraph.observability import SessionPropagatingSpanProcessor
        from opentelemetry.sdk.trace import SpanProcessor

        assert SessionPropagatingSpanProcessor is not None
        assert issubclass(SessionPropagatingSpanProcessor, SpanProcessor)

    def test_processor_implements_all_span_processor_methods(self) -> None:
        """
        GIVEN SessionPropagatingSpanProcessor
        WHEN checking its interface
        THEN it should implement all required SpanProcessor methods.
        """
        from mcp_server_langgraph.observability.session_propagating_span_processor import (
            SessionPropagatingSpanProcessor,
        )

        processor = SessionPropagatingSpanProcessor()

        # Verify all required methods exist
        assert hasattr(processor, "on_start")
        assert hasattr(processor, "on_end")
        assert hasattr(processor, "shutdown")
        assert hasattr(processor, "force_flush")

        # Verify callable
        assert callable(processor.on_start)
        assert callable(processor.on_end)
        assert callable(processor.shutdown)
        assert callable(processor.force_flush)

    def test_processor_force_flush_returns_true(self) -> None:
        """
        GIVEN SessionPropagatingSpanProcessor
        WHEN force_flush is called
        THEN it should return True (success).
        """
        from mcp_server_langgraph.observability.session_propagating_span_processor import (
            SessionPropagatingSpanProcessor,
        )

        processor = SessionPropagatingSpanProcessor()
        result = processor.force_flush()

        assert result is True

    def test_processor_shutdown_is_safe(self) -> None:
        """
        GIVEN SessionPropagatingSpanProcessor
        WHEN shutdown is called multiple times
        THEN it should not raise errors.
        """
        from mcp_server_langgraph.observability.session_propagating_span_processor import (
            SessionPropagatingSpanProcessor,
        )

        processor = SessionPropagatingSpanProcessor()

        # Multiple shutdowns should be safe
        processor.shutdown()
        processor.shutdown()
        processor.shutdown()


@pytest.mark.xdist_group("test_telemetry_module_integration")
class TestTelemetryModuleIntegration:
    """
    Tests for SessionPropagatingSpanProcessor integration in the telemetry module.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_telemetry_module_imports_processor(self) -> None:
        """
        GIVEN the telemetry.py module
        WHEN it's executed during observability initialization
        THEN it should be able to import SessionPropagatingSpanProcessor.
        """
        # This test verifies the import path works
        from mcp_server_langgraph.observability.session_propagating_span_processor import (
            SessionPropagatingSpanProcessor,
        )

        # Should not raise ImportError
        assert SessionPropagatingSpanProcessor is not None

    def test_processor_registered_before_broadcasting_processor(self) -> None:
        """
        GIVEN the telemetry.py module source
        WHEN examining the processor registration order
        THEN SessionPropagatingSpanProcessor should be added before BroadcastingSpanProcessor.
        """
        import inspect

        from mcp_server_langgraph.observability import telemetry

        # Get the source of _setup_tracing method
        source = inspect.getsource(telemetry.ObservabilityConfig._setup_tracing)

        # Find the positions of add_span_processor calls (not just class names)
        # This avoids false positives from comments mentioning processor names
        session_add = "add_span_processor(SessionPropagatingSpanProcessor())"
        broadcasting_add = "add_span_processor(BroadcastingSpanProcessor("

        session_pos = source.find(session_add)
        broadcasting_pos = source.find(broadcasting_add)

        # SessionPropagatingSpanProcessor should be added before BroadcastingSpanProcessor
        assert session_pos != -1, (
            f"SessionPropagatingSpanProcessor registration not found in telemetry. Expected: {session_add}"
        )
        assert broadcasting_pos != -1, (
            f"BroadcastingSpanProcessor registration not found in telemetry. Expected: {broadcasting_add}"
        )
        assert session_pos < broadcasting_pos, (
            "SessionPropagatingSpanProcessor should be registered before BroadcastingSpanProcessor"
        )


@pytest.mark.xdist_group("test_processor_behavior_with_mocks")
class TestProcessorBehaviorWithMocks:
    """
    Tests for processor behavior using mocks to avoid global OTEL state issues.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_on_start_propagates_session_id_from_parent(self) -> None:
        """
        GIVEN a parent span with session.id
        WHEN on_start is called for a child span
        THEN session.id should be propagated to the child.
        """
        from mcp_server_langgraph.observability.session_propagating_span_processor import (
            SessionPropagatingSpanProcessor,
        )

        processor = SessionPropagatingSpanProcessor()

        # Mock parent span with session.id
        parent_span = MagicMock()
        parent_span.attributes = {"session.id": "test-session-abc"}

        # Mock child span
        child_span = MagicMock()
        child_span.is_recording.return_value = True

        with patch(
            "mcp_server_langgraph.observability.session_propagating_span_processor.trace.get_current_span",
            return_value=parent_span,
        ):
            processor.on_start(child_span, parent_context=None)

        # Verify session.id was propagated
        child_span.set_attribute.assert_any_call("session.id", "test-session-abc")
        child_span.set_attribute.assert_any_call("session_id", "test-session-abc")
        child_span.set_attribute.assert_any_call("sessionId", "test-session-abc")

    def test_on_start_skips_when_no_session_id(self) -> None:
        """
        GIVEN a parent span without session.id
        WHEN on_start is called for a child span
        THEN no attributes should be set on the child.
        """
        from mcp_server_langgraph.observability.session_propagating_span_processor import (
            SessionPropagatingSpanProcessor,
        )

        processor = SessionPropagatingSpanProcessor()

        # Mock parent span without session.id
        parent_span = MagicMock()
        parent_span.attributes = {"other.attr": "value"}

        # Mock child span
        child_span = MagicMock()
        child_span.is_recording.return_value = True

        with patch(
            "mcp_server_langgraph.observability.session_propagating_span_processor.trace.get_current_span",
            return_value=parent_span,
        ):
            processor.on_start(child_span, parent_context=None)

        # Should not set any attributes
        child_span.set_attribute.assert_not_called()

    def test_on_start_handles_errors_gracefully(self) -> None:
        """
        GIVEN an error during propagation
        WHEN on_start is called
        THEN it should not raise and should log the error.
        """
        from mcp_server_langgraph.observability.session_propagating_span_processor import (
            SessionPropagatingSpanProcessor,
        )

        processor = SessionPropagatingSpanProcessor()

        # Mock parent span that raises on attribute access
        parent_span = MagicMock()
        parent_span.attributes = {"session.id": "test"}

        # Mock child span that raises on set_attribute
        child_span = MagicMock()
        child_span.is_recording.return_value = True
        child_span.set_attribute.side_effect = RuntimeError("Simulated error")

        with patch(
            "mcp_server_langgraph.observability.session_propagating_span_processor.trace.get_current_span",
            return_value=parent_span,
        ):
            # Should not raise
            processor.on_start(child_span, parent_context=None)


@pytest.mark.xdist_group("test_broadcasting_integration")
class TestBroadcastingIntegration:
    """
    Tests for integration between SessionPropagatingSpanProcessor and BroadcastingSpanProcessor.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_broadcasting_processor_can_be_instantiated_with_mock(self) -> None:
        """
        GIVEN BroadcastingSpanProcessor
        WHEN instantiated with a mock broadcaster
        THEN it should work without errors.
        """
        from mcp_server_langgraph.observability.broadcasting_span_processor import (
            BroadcastingSpanProcessor,
        )

        mock_broadcaster = MagicMock()
        processor = BroadcastingSpanProcessor(broadcaster=mock_broadcaster)

        assert processor is not None

    def test_processors_can_coexist_in_provider(self) -> None:
        """
        GIVEN both SessionPropagatingSpanProcessor and BroadcastingSpanProcessor
        WHEN added to the same TracerProvider
        THEN they should coexist without errors.
        """
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider

        from mcp_server_langgraph.observability.broadcasting_span_processor import (
            BroadcastingSpanProcessor,
        )
        from mcp_server_langgraph.observability.session_propagating_span_processor import (
            SessionPropagatingSpanProcessor,
        )

        mock_broadcaster = MagicMock()

        resource = Resource.create({"service.name": "test"})
        provider = TracerProvider(resource=resource)

        # Should not raise
        provider.add_span_processor(SessionPropagatingSpanProcessor())
        provider.add_span_processor(BroadcastingSpanProcessor(broadcaster=mock_broadcaster))

        provider.shutdown()
