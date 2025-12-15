"""
Audit context and OpenTelemetry trace correlation.

Provides utilities for:
- Extracting trace context from OpenTelemetry spans
- Creating AuditContext from HTTP requests
- Enriching audit events with trace correlation

This enables correlation between audit logs and distributed traces,
supporting comprehensive observability for compliance.
"""

import logging
from typing import Any
from uuid import uuid4

from opentelemetry import trace

from mcp_server_langgraph.audit.models import AuditContext

logger = logging.getLogger(__name__)


def get_trace_context() -> tuple[str | None, str | None]:
    """
    Extract trace context from the current OpenTelemetry span.

    Returns:
        Tuple of (trace_id, span_id) as hex strings, or (None, None) if no valid context.
    """
    try:
        span = trace.get_current_span()
        # Defensive check - get_current_span can return INVALID_SPAN which is falsy
        if span is None or not span.is_recording():
            return None, None

        span_context = span.get_span_context()
        if span_context is None or not span_context.is_valid:
            return None, None

        # Format as hex strings (32 chars for trace_id, 16 for span_id)
        trace_id = format(span_context.trace_id, "032x")
        span_id = format(span_context.span_id, "016x")

        return trace_id, span_id

    except Exception as e:
        logger.debug(
            "Failed to extract trace context",
            extra={"error": str(e)},
        )
        return None, None


def enrich_context_with_trace(context: AuditContext) -> AuditContext:
    """
    Enrich an AuditContext with OpenTelemetry trace information.

    Args:
        context: The audit context to enrich.

    Returns:
        New AuditContext with trace_id and span_id populated if available.
    """
    trace_id, span_id = get_trace_context()

    if trace_id is None and span_id is None:
        return context

    # Create a copy with trace info
    return AuditContext(
        request_id=context.request_id,
        session_id=context.session_id,
        ip_address=context.ip_address,
        user_agent=context.user_agent,
        trace_id=trace_id,
        span_id=span_id,
    )


def create_context_from_request(request: Any) -> AuditContext:
    """
    Create an AuditContext from an HTTP request.

    Extracts:
    - Request ID from request.state.request_id or generates one
    - IP address from request.client
    - User agent from headers
    - Trace context from OpenTelemetry

    Args:
        request: The FastAPI/Starlette Request object.

    Returns:
        Populated AuditContext.
    """
    # Extract request ID
    request_id = None
    if hasattr(request, "state"):
        request_id = getattr(request.state, "request_id", None)
    if request_id is None:
        request_id = str(uuid4())

    # Extract IP address
    ip_address = None
    if hasattr(request, "client") and request.client is not None:
        ip_address = request.client.host

    # Extract user agent
    user_agent = None
    if hasattr(request, "headers"):
        user_agent = request.headers.get("user-agent")

    # Extract session ID if available
    session_id = None
    if hasattr(request, "state"):
        sid = getattr(request.state, "session_id", None)
        if sid is not None and isinstance(sid, str):
            session_id = sid

    # Get trace context
    trace_id, span_id = get_trace_context()

    return AuditContext(
        request_id=request_id,
        session_id=session_id,
        ip_address=ip_address,
        user_agent=user_agent,
        trace_id=trace_id,
        span_id=span_id,
    )


def create_context_for_service(
    request_id: str | None = None,
    session_id: str | None = None,
) -> AuditContext:
    """
    Create an AuditContext for service-level operations.

    Use this when auditing operations not tied to HTTP requests.

    Args:
        request_id: Optional request ID.
        session_id: Optional session ID.

    Returns:
        AuditContext with trace correlation.
    """
    if request_id is None:
        request_id = str(uuid4())

    trace_id, span_id = get_trace_context()

    return AuditContext(
        request_id=request_id,
        session_id=session_id,
        trace_id=trace_id,
        span_id=span_id,
    )
