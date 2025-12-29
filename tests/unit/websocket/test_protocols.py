"""
Tests for WebSocket Protocol Pydantic Models.

TDD tests to verify that Python Pydantic models correctly match
the TypeScript websocket-protocols.ts types.
"""

import gc

import pytest
from pydantic import ValidationError

from mcp_server_langgraph.websocket.protocols import (
    # Protocol version
    PROTOCOL_VERSION,
    # DevTools
    ConsoleLevel,
    ConsoleLogEntry,
    ConsoleLogPayload,
    NetworkRequestEntry,
    NetworkRequestPayload,
    NetworkStatus,
    NetworkUpdateEntry,
    NetworkUpdatePayload,
    # Traces
    TraceEventEntry,
    TraceEventPayload,
    TraceSpanEntry,
    TraceSpanPayload,
    TraceSpanStatus,
    TraceSubscribeMessage,
    TraceSubscribePayload,
    # Budget Alerts
    BudgetAlertEntry,
    BudgetAlertPayload,
    BudgetAlertStatus,
    BudgetEntityType,
    BudgetSubscribedResponse,
    BudgetSubscribedPayload,
    BudgetSubscribeEntitiesMessage,
    BudgetSubscribeAllMessage,
    # AI Suggestions
    SuggestionResponseEntry,
    SuggestionResponsePayload,
    SuggestionRequestMessage,
    SuggestionRequestPayload,
    SuggestionAcceptMessage,
    SuggestionRejectMessage,
    ContextUpdateMessage,
    # MCP Aggregated
    MCPServerState,
    MCPServerStatusEntry,
    MCPServerStatusPayload,
    MCPToolCallEntry,
    MCPToolCallPayload,
    # Error
    WebSocketError,
    WebSocketErrorPayload,
    # Type guards
    is_console_log_entry,
    is_network_request_entry,
    is_network_update_entry,
    is_trace_span_entry,
    is_trace_event_entry,
    is_budget_alert_entry,
    is_suggestion_response_entry,
    is_websocket_error,
    # Validation helpers
    parse_message_envelope,
)

# Module-level pytest marker for test categorization
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="websocket_protocols")
class TestProtocolVersion:
    """Test protocol version."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_protocol_version_is_semver(self) -> None:
        """Protocol version should be valid semver."""
        parts = PROTOCOL_VERSION.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_protocol_version_current(self) -> None:
        """Protocol version should be 1.0.0."""
        assert PROTOCOL_VERSION == "1.0.0"


@pytest.mark.xdist_group(name="websocket_protocols")
class TestDevToolsProtocol:
    """Test DevTools protocol models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_console_log_entry_structure(self) -> None:
        """ConsoleLogEntry should have correct structure."""
        entry = ConsoleLogEntry(
            type="console",
            payload=ConsoleLogPayload(
                level=ConsoleLevel.INFO,
                message="Test message",
                timestamp="2025-01-01T00:00:00Z",
                source="test",
            ),
        )
        assert entry.type == "console"
        assert entry.payload.level == ConsoleLevel.INFO
        assert entry.payload.message == "Test message"

    def test_console_log_all_levels(self) -> None:
        """All console log levels should be valid."""
        for level in ConsoleLevel:
            payload = ConsoleLogPayload(
                level=level,
                message="test",
                timestamp="2025-01-01T00:00:00Z",
            )
            assert payload.level == level

    def test_network_request_entry_structure(self) -> None:
        """NetworkRequestEntry should have correct structure."""
        entry = NetworkRequestEntry(
            type="network",
            payload=NetworkRequestPayload(
                id="req-123",
                url="https://api.example.com/test",
                method="GET",
                timestamp="2025-01-01T00:00:00Z",
            ),
        )
        assert entry.type == "network"
        assert entry.payload.id == "req-123"
        assert entry.payload.method == "GET"
        assert entry.payload.status == NetworkStatus.PENDING

    def test_network_request_all_statuses(self) -> None:
        """All network statuses should be valid."""
        for status in NetworkStatus:
            payload = NetworkRequestPayload(
                id="req-123",
                url="https://test.com",
                method="GET",
                status=status,
                timestamp="2025-01-01T00:00:00Z",
            )
            assert payload.status == status

    def test_network_update_entry_structure(self) -> None:
        """NetworkUpdateEntry should have correct structure."""
        entry = NetworkUpdateEntry(
            type="network_update",
            payload=NetworkUpdatePayload(
                id="req-123",
                status=NetworkStatus.COMPLETE,
                status_code=200,
                duration_ms=150,
            ),
        )
        assert entry.type == "network_update"
        assert entry.payload.id == "req-123"
        assert entry.payload.status_code == 200


@pytest.mark.xdist_group(name="websocket_protocols")
class TestTracesProtocol:
    """Test Traces protocol models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_trace_span_entry_structure(self) -> None:
        """TraceSpanEntry should have correct structure."""
        entry = TraceSpanEntry(
            type="trace_span",
            payload=TraceSpanPayload(
                span_id="span-123",
                trace_id="trace-456",
                parent_span_id=None,
                name="http.request",
                start_time=1704067200000,
                end_time=1704067200100,
                duration_ms=100,
                status=TraceSpanStatus.OK,
                service_name="api-gateway",
                attributes={"http.method": "GET"},
            ),
        )
        assert entry.type == "trace_span"
        assert entry.payload.span_id == "span-123"
        assert entry.payload.status == TraceSpanStatus.OK

    def test_trace_span_all_statuses(self) -> None:
        """All trace span statuses should be valid."""
        for status in TraceSpanStatus:
            payload = TraceSpanPayload(
                span_id="span-123",
                trace_id="trace-456",
                parent_span_id=None,
                name="test",
                start_time=0,
                end_time=0,
                duration_ms=0,
                status=status,
                service_name="test",
            )
            assert payload.status == status

    def test_trace_event_entry_structure(self) -> None:
        """TraceEventEntry should have correct structure."""
        entry = TraceEventEntry(
            type="trace_event",
            payload=TraceEventPayload(
                span_id="span-123",
                name="http.request.start",
                timestamp="2025-01-01T00:00:00Z",
                attributes={"method": "GET"},
            ),
        )
        assert entry.type == "trace_event"
        assert entry.payload.span_id == "span-123"
        assert entry.payload.name == "http.request.start"

    def test_trace_subscribe_message_structure(self) -> None:
        """TraceSubscribeMessage should have correct structure."""
        msg = TraceSubscribeMessage(
            type="subscribe",
            id="sub-123",
            payload=TraceSubscribePayload(
                service_filter="api-*",
                trace_id="trace-456",
            ),
        )
        assert msg.type == "subscribe"
        assert msg.payload.service_filter == "api-*"


@pytest.mark.xdist_group(name="websocket_protocols")
class TestBudgetAlertsProtocol:
    """Test Budget Alerts protocol models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_budget_alert_entry_structure(self) -> None:
        """BudgetAlertEntry should have correct structure."""
        entry = BudgetAlertEntry(
            type="budget_alert",
            payload=BudgetAlertPayload(
                entity_type=BudgetEntityType.ORGANIZATION,
                entity_id="org-123",
                status=BudgetAlertStatus.WARNING,
                percent_used=85.5,
                current_spend="850.00",
                remaining="150.00",
                monthly_limit_usd="1000.00",
                message="Approaching budget limit",
            ),
        )
        assert entry.type == "budget_alert"
        assert entry.payload.entity_type == BudgetEntityType.ORGANIZATION
        assert entry.payload.status == BudgetAlertStatus.WARNING

    def test_budget_alert_all_statuses(self) -> None:
        """All budget alert statuses should be valid."""
        for status in BudgetAlertStatus:
            payload = BudgetAlertPayload(
                entity_type=BudgetEntityType.USER,
                entity_id="user-123",
                status=status,
                percent_used=0.0,
                current_spend="0",
                remaining="0",
                monthly_limit_usd="0",
            )
            assert payload.status == status

    def test_budget_subscribed_response_structure(self) -> None:
        """BudgetSubscribedResponse should have correct structure."""
        response = BudgetSubscribedResponse(
            type="subscribed",
            payload=BudgetSubscribedPayload(
                entity_ids=["org-1", "org-2"],
                subscribe_all=False,
            ),
        )
        assert response.type == "subscribed"
        assert len(response.payload.entity_ids) == 2

    def test_budget_subscribe_entities_message_structure(self) -> None:
        """BudgetSubscribeEntitiesMessage should have correct structure."""
        from mcp_server_langgraph.websocket.protocols import BudgetSubscribeEntitiesPayload

        msg = BudgetSubscribeEntitiesMessage(
            type="subscribe_entities",
            id="msg-123",
            payload=BudgetSubscribeEntitiesPayload(entity_ids=["org-1", "org-2"]),
        )
        assert msg.type == "subscribe_entities"
        assert len(msg.payload.entity_ids) == 2

    def test_budget_subscribe_all_message_structure(self) -> None:
        """BudgetSubscribeAllMessage should have correct structure."""
        msg = BudgetSubscribeAllMessage(
            type="subscribe_all",
            id="msg-123",
        )
        assert msg.type == "subscribe_all"


@pytest.mark.xdist_group(name="websocket_protocols")
class TestAISuggestionsProtocol:
    """Test AI Suggestions protocol models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_suggestion_response_entry_structure(self) -> None:
        """SuggestionResponseEntry should have correct structure."""
        entry = SuggestionResponseEntry(
            type="suggestion_response",
            payload=SuggestionResponsePayload(
                suggestion_id="sug-123",
                text="Suggested completion",
                confidence=0.95,
                reasoning="Based on context",
            ),
        )
        assert entry.type == "suggestion_response"
        assert entry.payload.suggestion_id == "sug-123"
        assert entry.payload.confidence == 0.95

    def test_suggestion_request_message_structure(self) -> None:
        """SuggestionRequestMessage should have correct structure."""
        msg = SuggestionRequestMessage(
            type="suggestion_request",
            id="req-123",
            payload=SuggestionRequestPayload(
                session_id="session-456",
                input_text="def hello",
                cursor_position=9,
                context_window=500,
            ),
        )
        assert msg.type == "suggestion_request"
        assert msg.payload.session_id == "session-456"

    def test_suggestion_accept_message_structure(self) -> None:
        """SuggestionAcceptMessage should have correct structure."""
        from mcp_server_langgraph.websocket.protocols import SuggestionAcceptPayload

        msg = SuggestionAcceptMessage(
            type="suggestion_accept",
            id="msg-123",
            payload=SuggestionAcceptPayload(suggestion_id="sug-123"),
        )
        assert msg.type == "suggestion_accept"
        assert msg.payload.suggestion_id == "sug-123"

    def test_suggestion_reject_message_structure(self) -> None:
        """SuggestionRejectMessage should have correct structure."""
        from mcp_server_langgraph.websocket.protocols import SuggestionRejectPayload

        msg = SuggestionRejectMessage(
            type="suggestion_reject",
            id="msg-123",
            payload=SuggestionRejectPayload(
                suggestion_id="sug-123",
                reason="Not relevant",
            ),
        )
        assert msg.type == "suggestion_reject"
        assert msg.payload.reason == "Not relevant"

    def test_context_update_message_structure(self) -> None:
        """ContextUpdateMessage should have correct structure."""
        from mcp_server_langgraph.websocket.protocols import ContextUpdatePayload

        msg = ContextUpdateMessage(
            type="context_update",
            id="msg-123",
            payload=ContextUpdatePayload(
                session_id="session-456",
                context="Current file context...",
            ),
        )
        assert msg.type == "context_update"
        assert msg.payload.session_id == "session-456"


@pytest.mark.xdist_group(name="websocket_protocols")
class TestMCPAggregatedProtocol:
    """Test MCP Aggregated protocol models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_mcp_server_status_entry_structure(self) -> None:
        """MCPServerStatusEntry should have correct structure."""
        entry = MCPServerStatusEntry(
            type="server_status",
            payload=MCPServerStatusPayload(
                server_id="server-123",
                name="calculator",
                status=MCPServerState.CONNECTED,
                tools_count=5,
                last_seen="2025-01-01T00:00:00Z",
            ),
        )
        assert entry.type == "server_status"
        assert entry.payload.server_id == "server-123"
        assert entry.payload.status == MCPServerState.CONNECTED

    def test_mcp_server_all_states(self) -> None:
        """All MCP server states should be valid."""
        for state in MCPServerState:
            payload = MCPServerStatusPayload(
                server_id="server-123",
                name="test",
                status=state,
            )
            assert payload.status == state

    def test_mcp_tool_call_entry_structure(self) -> None:
        """MCPToolCallEntry should have correct structure."""
        entry = MCPToolCallEntry(
            type="tool_call",
            payload=MCPToolCallPayload(
                call_id="call-123",
                server_id="server-456",
                tool_name="calculate",
                arguments={"a": 1, "b": 2},
                status="completed",
                result=3,
            ),
        )
        assert entry.type == "tool_call"
        assert entry.payload.tool_name == "calculate"
        assert entry.payload.result == 3


@pytest.mark.xdist_group(name="websocket_protocols")
class TestWebSocketError:
    """Test WebSocket error models."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_error_structure(self) -> None:
        """WebSocketError should have correct structure."""
        error = WebSocketError(
            type="error",
            payload=WebSocketErrorPayload(
                code="internal_error",
                message="Something went wrong",
                retryable=True,
            ),
        )
        assert error.type == "error"
        assert error.payload.code == "internal_error"
        assert error.payload.retryable is True


@pytest.mark.xdist_group(name="websocket_protocols")
class TestTypeGuards:
    """Test type guard functions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_is_console_log_entry_valid(self) -> None:
        """is_console_log_entry should return True for valid entry."""
        data = {"type": "console", "payload": {"level": "info", "message": "test"}}
        assert is_console_log_entry(data) is True

    def test_is_console_log_entry_invalid(self) -> None:
        """is_console_log_entry should return False for invalid entry."""
        assert is_console_log_entry({"type": "network"}) is False
        assert is_console_log_entry({"type": "console"}) is False
        assert is_console_log_entry({}) is False

    def test_is_network_request_entry_valid(self) -> None:
        """is_network_request_entry should return True for valid entry."""
        data = {"type": "network", "payload": {"id": "req-123"}}
        assert is_network_request_entry(data) is True

    def test_is_network_request_entry_invalid(self) -> None:
        """is_network_request_entry should return False for invalid entry."""
        assert is_network_request_entry({"type": "console"}) is False

    def test_is_network_update_entry_valid(self) -> None:
        """is_network_update_entry should return True for valid entry."""
        data = {"type": "network_update", "payload": {"id": "req-123"}}
        assert is_network_update_entry(data) is True

    def test_is_network_update_entry_invalid(self) -> None:
        """is_network_update_entry should return False for invalid entry."""
        assert is_network_update_entry({"type": "network"}) is False

    def test_is_trace_span_entry_valid(self) -> None:
        """is_trace_span_entry should return True for valid entry."""
        data = {"type": "trace_span", "payload": {"span_id": "span-123"}}
        assert is_trace_span_entry(data) is True

    def test_is_trace_span_entry_invalid(self) -> None:
        """is_trace_span_entry should return False for invalid entry."""
        assert is_trace_span_entry({"type": "console"}) is False

    def test_is_trace_event_entry_valid(self) -> None:
        """is_trace_event_entry should return True for valid entry."""
        data = {"type": "trace_event", "payload": {"span_id": "span-123"}}
        assert is_trace_event_entry(data) is True

    def test_is_trace_event_entry_invalid(self) -> None:
        """is_trace_event_entry should return False for invalid entry."""
        assert is_trace_event_entry({"type": "trace_span"}) is False

    def test_is_budget_alert_entry_valid(self) -> None:
        """is_budget_alert_entry should return True for valid entry."""
        data = {"type": "budget_alert", "payload": {"entity_id": "org-123"}}
        assert is_budget_alert_entry(data) is True

    def test_is_budget_alert_entry_invalid(self) -> None:
        """is_budget_alert_entry should return False for invalid entry."""
        assert is_budget_alert_entry({"type": "console"}) is False

    def test_is_suggestion_response_entry_valid(self) -> None:
        """is_suggestion_response_entry should return True for valid entry."""
        data = {"type": "suggestion_response", "payload": {"suggestion_id": "sug-123"}}
        assert is_suggestion_response_entry(data) is True

    def test_is_suggestion_response_entry_invalid(self) -> None:
        """is_suggestion_response_entry should return False for invalid entry."""
        assert is_suggestion_response_entry({"type": "suggestion_request"}) is False

    def test_is_websocket_error_valid(self) -> None:
        """is_websocket_error should return True for valid error."""
        data = {"type": "error", "payload": {"code": "internal_error"}}
        assert is_websocket_error(data) is True

    def test_is_websocket_error_invalid(self) -> None:
        """is_websocket_error should return False for invalid entry."""
        assert is_websocket_error({"type": "console"}) is False


@pytest.mark.xdist_group(name="websocket_protocols")
class TestParseMessageEnvelope:
    """Test parse_message_envelope function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_parse_console_log_entry(self) -> None:
        """parse_message_envelope should return ConsoleLogEntry."""
        data = {
            "type": "console",
            "payload": {
                "level": "info",
                "message": "test",
                "timestamp": "2025-01-01T00:00:00Z",
            },
        }
        result = parse_message_envelope(data)
        assert isinstance(result, ConsoleLogEntry)

    def test_parse_trace_span_entry(self) -> None:
        """parse_message_envelope should return TraceSpanEntry."""
        data = {
            "type": "trace_span",
            "payload": {
                "span_id": "span-123",
                "trace_id": "trace-456",
                "parent_span_id": None,
                "name": "test",
                "start_time": 0,
                "end_time": 0,
                "duration_ms": 0,
                "status": "ok",
                "service_name": "test",
            },
        }
        result = parse_message_envelope(data)
        assert isinstance(result, TraceSpanEntry)

    def test_parse_trace_event_entry(self) -> None:
        """parse_message_envelope should return TraceEventEntry."""
        data = {
            "type": "trace_event",
            "payload": {
                "span_id": "span-123",
                "name": "event",
                "timestamp": "2025-01-01T00:00:00Z",
            },
        }
        result = parse_message_envelope(data)
        assert isinstance(result, TraceEventEntry)

    def test_parse_websocket_error(self) -> None:
        """parse_message_envelope should return WebSocketError."""
        data = {
            "type": "error",
            "payload": {
                "code": "internal_error",
                "message": "Something went wrong",
            },
        }
        result = parse_message_envelope(data)
        assert isinstance(result, WebSocketError)

    def test_parse_unknown_type_returns_base(self) -> None:
        """parse_message_envelope should return MessageEnvelopeBase for unknown types."""
        from mcp_server_langgraph.websocket.protocols import MessageEnvelopeBase

        data = {"type": "unknown_type", "payload": {"foo": "bar"}}
        result = parse_message_envelope(data)
        assert isinstance(result, MessageEnvelopeBase)
        assert result.type == "unknown_type"


@pytest.mark.xdist_group(name="websocket_protocols")
class TestValidation:
    """Test Pydantic validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_console_log_missing_required_field(self) -> None:
        """ConsoleLogPayload should fail validation for missing required field."""
        with pytest.raises(ValidationError):
            ConsoleLogPayload(level=ConsoleLevel.INFO, message="test")  # type: ignore - missing timestamp

    def test_trace_span_invalid_status(self) -> None:
        """TraceSpanPayload should fail validation for invalid status."""
        with pytest.raises(ValidationError):
            TraceSpanPayload(
                span_id="span-123",
                trace_id="trace-456",
                parent_span_id=None,
                name="test",
                start_time=0,
                end_time=0,
                duration_ms=0,
                status="invalid_status",  # type: ignore
                service_name="test",
            )

    def test_json_serialization_roundtrip(self) -> None:
        """Models should serialize to JSON and back correctly."""
        original = ConsoleLogEntry(
            type="console",
            payload=ConsoleLogPayload(
                level=ConsoleLevel.WARN,
                message="Warning message",
                timestamp="2025-01-01T00:00:00Z",
                source="test",
                data={"extra": "info"},
            ),
        )

        # Serialize to dict (JSON-compatible)
        json_data = original.model_dump()

        # Deserialize back
        restored = ConsoleLogEntry.model_validate(json_data)

        assert restored.type == original.type
        assert restored.payload.level == original.payload.level
        assert restored.payload.message == original.payload.message
        assert restored.payload.data == original.payload.data

    def test_json_schema_generation(self) -> None:
        """Models should generate JSON schema."""
        schema = ConsoleLogEntry.model_json_schema()

        assert "properties" in schema
        assert "type" in schema["properties"]
        assert "payload" in schema["properties"]
