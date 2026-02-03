"""SpanProcessor that propagates session.id from parent to child spans.

This ensures all LangGraph internal spans (node, LLM, tool, retriever) have
session.id set, enabling DevTools trace visualization.

Architecture Decision (Triple-AI Review - Claude + Codex + Gemini):
- Uses SpanProcessor instead of LangChain callbacks for reliability
- SpanProcessor.on_start is called for EVERY span, guaranteed
- No timing issues with callback execution context
- Works for all span types automatically
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.sdk.trace import SpanProcessor

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import ReadableSpan, Span

logger = logging.getLogger(__name__)


class SessionPropagatingSpanProcessor(SpanProcessor):
    """Propagates session.id attribute from parent span to all child spans.

    This processor runs on_start for every span and copies the session.id
    from the parent span (if present) to the child span. This ensures that
    LangGraph internal spans have session.id set for DevTools trace rendering.

    Security Note:
        session.id is server-generated (UUID) and validated by the session
        management layer. It is NOT user-controllable input. Authorization
        checks are performed by DevToolsBroadcaster before emitting traces
        to WebSocket subscribers.

    Example:
        >>> from opentelemetry.sdk.trace import TracerProvider
        >>> provider = TracerProvider()
        >>> provider.add_span_processor(SessionPropagatingSpanProcessor())

    Triple-AI Review:
        This approach was chosen over LangChain callbacks because:
        1. SpanProcessor.on_start is called for EVERY span, guaranteed
        2. No timing issues with callback execution context
        3. Works for all span types (chain, LLM, tool, retriever)
    """

    def on_start(self, span: Span, parent_context: Context | None = None) -> None:
        """Called when a span starts. Propagates session.id from parent.

        Args:
            span: The span that just started.
            parent_context: The parent context (optional).
        """
        if not span.is_recording():
            return

        try:
            # Get parent span from provided context, or fall back to current context
            # parent_context is provided when spans are created with explicit parents
            # (common in async scenarios and context propagation)
            parent_span = trace.get_current_span(parent_context) if parent_context is not None else trace.get_current_span()
            if parent_span is None:
                return

            # Get parent attributes (handle both Span and ReadableSpan)
            parent_attrs = getattr(parent_span, "attributes", None)
            if parent_attrs is None:
                return

            # Check all three variants of session.id (priority order)
            session_id = parent_attrs.get("session.id") or parent_attrs.get("session_id") or parent_attrs.get("sessionId")

            # Guard: Don't propagate empty/None session_id
            if not session_id:
                return

            # Convert to string and propagate to child span
            # (all three variants for compatibility with different consumers)
            session_id_str = str(session_id)
            span.set_attribute("session.id", session_id_str)
            span.set_attribute("session_id", session_id_str)
            span.set_attribute("sessionId", session_id_str)

        except Exception as exc:
            # Best-effort: don't break tracing if propagation fails
            logger.debug("Failed to propagate session.id to span: %s", exc)

    def on_end(self, span: ReadableSpan) -> None:
        """Called when a span ends. No-op for this processor.

        Args:
            span: The span that just ended.
        """
        pass

    def shutdown(self) -> None:
        """Shutdown the processor. No-op for this processor."""
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush pending data. No-op for this processor.

        Args:
            timeout_millis: Maximum time to wait for flush (unused).

        Returns:
            True (always succeeds as there's nothing to flush).
        """
        return True
