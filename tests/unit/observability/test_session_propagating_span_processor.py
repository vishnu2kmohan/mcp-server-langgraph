"""
Tests for SessionPropagatingSpanProcessor.

This processor propagates session.id from parent spans to child spans,
enabling DevTools trace visualization for LangGraph agent execution.

TDD: These tests define the expected behavior BEFORE implementation.

Triple-AI Review: This approach was chosen over LangChain callbacks because:
- SpanProcessor.on_start is called for EVERY span, guaranteed
- No timing issues with callback execution context
- Works for all span types (chain, LLM, tool, retriever)
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

# Module-level markers
pytestmark = [
    pytest.mark.unit,
    pytest.mark.observability,
    pytest.mark.xdist_group(name="session_propagating_span_processor"),
    pytest.mark.skip_observability_init,  # Skip global OTEL init for isolated testing
]


class TestSessionPropagatingSpanProcessor:
    """
    Unit tests for SessionPropagatingSpanProcessor.

    The SessionPropagatingSpanProcessor implements OpenTelemetry's SpanProcessor interface
    and propagates session.id from parent spans to all child spans on_start.

    This ensures LangGraph internal spans have session.id for DevTools trace rendering.
    """

    def test_processor_implements_span_processor_interface(self) -> None:
        """
        GIVEN SessionPropagatingSpanProcessor
        WHEN instantiated
        THEN it should implement the SpanProcessor interface.
        """
        from opentelemetry.sdk.trace import SpanProcessor

        from mcp_server_langgraph.observability.session_propagating_span_processor import (
            SessionPropagatingSpanProcessor,
        )

        processor = SessionPropagatingSpanProcessor()

        assert isinstance(processor, SpanProcessor)

    def test_propagates_session_id_from_parent_span(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN a parent span with session.id attribute
        WHEN on_start is called for a child span
        THEN the child span should receive session.id from the parent.
        """
        import mcp_server_langgraph.observability.session_propagating_span_processor as mod

        # Create mock parent span with session.id
        parent_span = MagicMock()
        parent_span.attributes = {"session.id": "test-session-123"}

        # Patch get_current_span using monkeypatch
        monkeypatch.setattr(mod.trace, "get_current_span", lambda: parent_span)

        processor = mod.SessionPropagatingSpanProcessor()

        # Create mock child span (recording)
        child_span = MagicMock()
        child_span.is_recording.return_value = True

        processor.on_start(child_span, parent_context=None)

        # Verify session.id was propagated (all three variants)
        child_span.set_attribute.assert_any_call("session.id", "test-session-123")
        child_span.set_attribute.assert_any_call("session_id", "test-session-123")
        child_span.set_attribute.assert_any_call("sessionId", "test-session-123")

    def test_propagates_session_id_using_explicit_parent_context(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN a parent span with session.id in an explicit parent_context
        WHEN on_start is called with that parent_context
        THEN the session.id should be read from the provided context, not current.

        This is critical for async scenarios where spans are created with
        explicit parent contexts for context propagation.
        """
        import mcp_server_langgraph.observability.session_propagating_span_processor as mod
        from opentelemetry.context import Context

        # Create mock parent span with session.id
        parent_span = MagicMock()
        parent_span.attributes = {"session.id": "async-session-456"}

        # Track which context was passed to get_current_span
        call_args: list = []

        def mock_get_current_span(context=None):
            call_args.append(context)
            return parent_span

        monkeypatch.setattr(mod.trace, "get_current_span", mock_get_current_span)

        processor = mod.SessionPropagatingSpanProcessor()

        child_span = MagicMock()
        child_span.is_recording.return_value = True

        # Create explicit parent context
        explicit_context = Context()

        # Call with explicit parent_context
        processor.on_start(child_span, parent_context=explicit_context)

        # Verify get_current_span was called with the explicit context
        assert len(call_args) == 1, "get_current_span should be called once"
        assert call_args[0] is explicit_context, "get_current_span should receive the explicit parent_context"

        # Verify session.id was propagated
        child_span.set_attribute.assert_any_call("session.id", "async-session-456")

    def test_handles_missing_parent_gracefully(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN no parent span in context
        WHEN on_start is called for a span
        THEN it should not raise an error and not set any attributes.
        """
        import mcp_server_langgraph.observability.session_propagating_span_processor as mod

        # Patch get_current_span to return None
        monkeypatch.setattr(mod.trace, "get_current_span", lambda: None)

        processor = mod.SessionPropagatingSpanProcessor()

        child_span = MagicMock()
        child_span.is_recording.return_value = True

        # Should not raise
        processor.on_start(child_span, parent_context=None)

        # Should not set any attributes
        child_span.set_attribute.assert_not_called()

    def test_handles_parent_without_attributes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN a parent span without attributes
        WHEN on_start is called for a child span
        THEN it should not raise an error and not set any attributes.
        """
        import mcp_server_langgraph.observability.session_propagating_span_processor as mod

        # Parent span without attributes attribute
        parent_span = MagicMock(spec=[])  # No attributes
        monkeypatch.setattr(mod.trace, "get_current_span", lambda: parent_span)

        processor = mod.SessionPropagatingSpanProcessor()

        child_span = MagicMock()
        child_span.is_recording.return_value = True

        # Should not raise
        processor.on_start(child_span, parent_context=None)

        # Should not set any attributes
        child_span.set_attribute.assert_not_called()

    def test_skips_non_recording_spans(self) -> None:
        """
        GIVEN a non-recording span
        WHEN on_start is called
        THEN it should skip processing and not set any attributes.
        """
        from mcp_server_langgraph.observability.session_propagating_span_processor import (
            SessionPropagatingSpanProcessor,
        )

        processor = SessionPropagatingSpanProcessor()

        child_span = MagicMock()
        child_span.is_recording.return_value = False

        processor.on_start(child_span, parent_context=None)

        child_span.set_attribute.assert_not_called()

    def test_handles_empty_session_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN a parent span with empty session.id
        WHEN on_start is called for a child span
        THEN it should not propagate the empty value.
        """
        import mcp_server_langgraph.observability.session_propagating_span_processor as mod

        parent_span = MagicMock()
        parent_span.attributes = {"session.id": ""}  # Empty
        monkeypatch.setattr(mod.trace, "get_current_span", lambda: parent_span)

        processor = mod.SessionPropagatingSpanProcessor()

        child_span = MagicMock()
        child_span.is_recording.return_value = True

        processor.on_start(child_span, parent_context=None)

        # Should not propagate empty session.id
        child_span.set_attribute.assert_not_called()

    def test_handles_none_session_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN a parent span with None session.id
        WHEN on_start is called for a child span
        THEN it should not propagate the None value.
        """
        import mcp_server_langgraph.observability.session_propagating_span_processor as mod

        parent_span = MagicMock()
        parent_span.attributes = {"session.id": None}
        monkeypatch.setattr(mod.trace, "get_current_span", lambda: parent_span)

        processor = mod.SessionPropagatingSpanProcessor()

        child_span = MagicMock()
        child_span.is_recording.return_value = True

        processor.on_start(child_span, parent_context=None)

        # Should not propagate None session.id
        child_span.set_attribute.assert_not_called()

    def test_checks_session_id_snake_case_variant(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN a parent span with session_id (snake_case) attribute
        WHEN on_start is called for a child span
        THEN it should propagate the session_id value.
        """
        import mcp_server_langgraph.observability.session_propagating_span_processor as mod

        parent_span = MagicMock()
        parent_span.attributes = {"session_id": "snake-case-session-456"}
        monkeypatch.setattr(mod.trace, "get_current_span", lambda: parent_span)

        processor = mod.SessionPropagatingSpanProcessor()

        child_span = MagicMock()
        child_span.is_recording.return_value = True

        processor.on_start(child_span, parent_context=None)

        child_span.set_attribute.assert_any_call("session.id", "snake-case-session-456")

    def test_checks_sessionId_camel_case_variant(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN a parent span with sessionId (camelCase) attribute
        WHEN on_start is called for a child span
        THEN it should propagate the sessionId value.
        """
        import mcp_server_langgraph.observability.session_propagating_span_processor as mod

        parent_span = MagicMock()
        parent_span.attributes = {"sessionId": "camel-case-session-789"}
        monkeypatch.setattr(mod.trace, "get_current_span", lambda: parent_span)

        processor = mod.SessionPropagatingSpanProcessor()

        child_span = MagicMock()
        child_span.is_recording.return_value = True

        processor.on_start(child_span, parent_context=None)

        child_span.set_attribute.assert_any_call("session.id", "camel-case-session-789")

    def test_prefers_session_dot_id_over_variants(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN a parent span with all three session.id variants
        WHEN on_start is called for a child span
        THEN it should use session.id (dotted) as the priority.
        """
        import mcp_server_langgraph.observability.session_propagating_span_processor as mod

        parent_span = MagicMock()
        parent_span.attributes = {
            "session.id": "dotted-priority",
            "session_id": "snake-case-fallback",
            "sessionId": "camel-case-fallback",
        }
        monkeypatch.setattr(mod.trace, "get_current_span", lambda: parent_span)

        processor = mod.SessionPropagatingSpanProcessor()

        child_span = MagicMock()
        child_span.is_recording.return_value = True

        processor.on_start(child_span, parent_context=None)

        # Should use the dotted variant value
        child_span.set_attribute.assert_any_call("session.id", "dotted-priority")

    def test_on_end_is_noop(self) -> None:
        """
        GIVEN SessionPropagatingSpanProcessor
        WHEN on_end is called
        THEN it should be a no-op (not raise).
        """
        from mcp_server_langgraph.observability.session_propagating_span_processor import (
            SessionPropagatingSpanProcessor,
        )

        processor = SessionPropagatingSpanProcessor()

        mock_span = MagicMock()

        # Should not raise
        processor.on_end(mock_span)

    def test_shutdown_is_noop(self) -> None:
        """
        GIVEN SessionPropagatingSpanProcessor
        WHEN shutdown is called
        THEN it should be a no-op (not raise).
        """
        from mcp_server_langgraph.observability.session_propagating_span_processor import (
            SessionPropagatingSpanProcessor,
        )

        processor = SessionPropagatingSpanProcessor()

        # Should not raise
        processor.shutdown()

    def test_force_flush_returns_true(self) -> None:
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

    def test_handles_exception_during_propagation_gracefully(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN an error occurs during session.id propagation
        WHEN on_start is called
        THEN it should catch the exception and not raise (best-effort).
        """
        import mcp_server_langgraph.observability.session_propagating_span_processor as mod

        # Parent span that has session.id
        parent_span = MagicMock()
        parent_span.attributes = {"session.id": "test-session"}
        monkeypatch.setattr(mod.trace, "get_current_span", lambda: parent_span)

        processor = mod.SessionPropagatingSpanProcessor()

        child_span = MagicMock()
        child_span.is_recording.return_value = True
        child_span.set_attribute.side_effect = RuntimeError("Simulated error")

        # Should not raise
        processor.on_start(child_span, parent_context=None)

    def test_converts_session_id_to_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """
        GIVEN a parent span with non-string session.id (e.g., UUID object)
        WHEN on_start is called for a child span
        THEN it should convert the value to string before setting.
        """
        import mcp_server_langgraph.observability.session_propagating_span_processor as mod

        # Simulate a UUID-like object
        class FakeUUID:
            def __str__(self) -> str:
                return "uuid-as-string-12345"

        parent_span = MagicMock()
        parent_span.attributes = {"session.id": FakeUUID()}
        monkeypatch.setattr(mod.trace, "get_current_span", lambda: parent_span)

        processor = mod.SessionPropagatingSpanProcessor()

        child_span = MagicMock()
        child_span.is_recording.return_value = True

        processor.on_start(child_span, parent_context=None)

        # Should convert to string
        child_span.set_attribute.assert_any_call("session.id", "uuid-as-string-12345")
