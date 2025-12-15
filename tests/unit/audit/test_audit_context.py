"""
Tests for audit context and trace correlation.

TDD RED phase: These tests define expected behavior for trace correlation.

The context module should:
- Extract trace_id and span_id from OpenTelemetry context
- Provide fallback when no trace context exists
- Integrate with AuditContext model
"""

import gc
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_context")
class TestAuditTraceCorrelation:
    """Tests for OpenTelemetry trace correlation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_extract_trace_context_from_span(self) -> None:
        """GIVEN active span WHEN extracting THEN trace_id and span_id returned."""
        from mcp_server_langgraph.audit.context import get_trace_context

        with patch("mcp_server_langgraph.audit.context.trace") as mock_trace:
            mock_span = MagicMock()
            mock_span_context = MagicMock()
            mock_span_context.trace_id = 0x0AF7651916CD43DD8448EB211C80319C
            mock_span_context.span_id = 0xB7AD6B7169203331
            mock_span_context.is_valid = True
            mock_span.get_span_context.return_value = mock_span_context

            mock_trace.get_current_span.return_value = mock_span

            trace_id, span_id = get_trace_context()

            assert trace_id is not None
            assert span_id is not None
            # Trace ID should be 32 hex characters
            assert len(trace_id) == 32
            # Span ID should be 16 hex characters
            assert len(span_id) == 16

    def test_extract_trace_context_no_span(self) -> None:
        """GIVEN no active span WHEN extracting THEN None returned."""
        from mcp_server_langgraph.audit.context import get_trace_context

        with patch("mcp_server_langgraph.audit.context.trace") as mock_trace:
            mock_span = MagicMock()
            mock_span_context = MagicMock()
            mock_span_context.is_valid = False
            mock_span.get_span_context.return_value = mock_span_context

            mock_trace.get_current_span.return_value = mock_span

            trace_id, span_id = get_trace_context()

            assert trace_id is None
            assert span_id is None

    def test_enrich_audit_context_with_trace(self) -> None:
        """GIVEN audit context WHEN enriched THEN trace info added."""
        from mcp_server_langgraph.audit.context import enrich_context_with_trace
        from mcp_server_langgraph.audit.models import AuditContext

        context = AuditContext(request_id="req-001")

        with patch("mcp_server_langgraph.audit.context.get_trace_context") as mock_get:
            mock_get.return_value = ("0af7651916cd43dd8448eb211c80319c", "b7ad6b7169203331")

            enriched = enrich_context_with_trace(context)

            assert enriched.trace_id == "0af7651916cd43dd8448eb211c80319c"
            assert enriched.span_id == "b7ad6b7169203331"
            assert enriched.request_id == "req-001"

    def test_enrich_audit_context_no_trace(self) -> None:
        """GIVEN audit context WHEN no trace THEN original context returned."""
        from mcp_server_langgraph.audit.context import enrich_context_with_trace
        from mcp_server_langgraph.audit.models import AuditContext

        context = AuditContext(request_id="req-001")

        with patch("mcp_server_langgraph.audit.context.get_trace_context") as mock_get:
            mock_get.return_value = (None, None)

            enriched = enrich_context_with_trace(context)

            assert enriched.trace_id is None
            assert enriched.span_id is None
            assert enriched.request_id == "req-001"


@pytest.mark.unit
@pytest.mark.xdist_group(name="audit_context")
class TestAuditRequestContext:
    """Tests for request context propagation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_context_from_request(self) -> None:
        """GIVEN HTTP request WHEN creating context THEN all fields populated."""
        from mcp_server_langgraph.audit.context import create_context_from_request

        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.100"
        mock_request.headers = {"user-agent": "TestClient/1.0"}
        mock_request.state.request_id = "req-test-001"

        with patch("mcp_server_langgraph.audit.context.get_trace_context") as mock_get:
            mock_get.return_value = ("trace123", "span456")

            context = create_context_from_request(mock_request)

            assert context.request_id == "req-test-001"
            assert context.ip_address == "192.168.1.100"
            assert context.user_agent == "TestClient/1.0"
            assert context.trace_id == "trace123"
            assert context.span_id == "span456"

    def test_create_context_handles_missing_client(self) -> None:
        """GIVEN request without client WHEN creating context THEN handles gracefully."""
        from mcp_server_langgraph.audit.context import create_context_from_request

        mock_request = MagicMock()
        mock_request.client = None
        mock_request.headers = {}
        mock_request.state.request_id = "req-001"

        with patch("mcp_server_langgraph.audit.context.get_trace_context") as mock_get:
            mock_get.return_value = (None, None)

            context = create_context_from_request(mock_request)

            assert context.request_id == "req-001"
            assert context.ip_address is None

    def test_create_context_generates_request_id_if_missing(self) -> None:
        """GIVEN request without request_id WHEN creating context THEN ID generated."""
        from mcp_server_langgraph.audit.context import create_context_from_request

        mock_request = MagicMock()
        mock_request.client = None
        mock_request.headers = {}
        # No request_id in state
        mock_request.state = MagicMock(spec=[])  # Empty spec means no attributes

        with patch("mcp_server_langgraph.audit.context.get_trace_context") as mock_get:
            mock_get.return_value = (None, None)

            context = create_context_from_request(mock_request)

            assert context.request_id is not None
            assert len(context.request_id) > 0
