"""
Tests for HITL Agent Request Broadcasting.

Tests cover:
- AgentRequestWSMessageType enum
- Message models (ApprovalRequired, ClarificationRequired, etc.)
- WebSocketConnection class
- AgentRequestBroadcaster class
"""

from __future__ import annotations

import gc
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.hitl.broadcast import (
    AgentRequestBroadcaster,
    AgentRequestWSMessageType,
    ApprovalRequiredMessage,
    ApprovalUpdatedMessage,
    ClarificationRequiredMessage,
    ExecutionResumedMessage,
    WebSocketConnection,
)


# Module-level marker for test discovery
pytestmark = pytest.mark.unit

# =============================================================================
# Message Type Enum Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="hitl_broadcast")
class TestAgentRequestWSMessageType:
    """Tests for AgentRequestWSMessageType enum."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_approval_required_value(self) -> None:
        """Test APPROVAL_REQUIRED has correct value."""
        assert AgentRequestWSMessageType.APPROVAL_REQUIRED == "approval_required"

    def test_clarification_required_value(self) -> None:
        """Test CLARIFICATION_REQUIRED has correct value."""
        assert AgentRequestWSMessageType.CLARIFICATION_REQUIRED == "clarification_required"

    def test_approval_updated_value(self) -> None:
        """Test APPROVAL_UPDATED has correct value."""
        assert AgentRequestWSMessageType.APPROVAL_UPDATED == "approval_updated"

    def test_execution_resumed_value(self) -> None:
        """Test EXECUTION_RESUMED has correct value."""
        assert AgentRequestWSMessageType.EXECUTION_RESUMED == "execution_resumed"

    def test_pong_value(self) -> None:
        """Test PONG has correct value."""
        assert AgentRequestWSMessageType.PONG == "pong"

    def test_error_value(self) -> None:
        """Test ERROR has correct value."""
        assert AgentRequestWSMessageType.ERROR == "error"

    def test_all_message_types_are_strings(self) -> None:
        """Verify all message types are strings."""
        for msg_type in AgentRequestWSMessageType:
            assert isinstance(msg_type.value, str)


# =============================================================================
# Message Model Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="hitl_broadcast")
class TestApprovalRequiredMessage:
    """Tests for ApprovalRequiredMessage model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_valid_message(self) -> None:
        """Test creating a valid ApprovalRequiredMessage."""
        msg = ApprovalRequiredMessage(
            request_id="req-123",
            session_id="sess-456",
            task_id="task-789",
            agent_name="test-agent",
            confidence=0.75,
            threshold=0.80,
            proposed_action="Delete all files",
            trigger_reason="Low confidence",
            requested_at="2025-01-01T00:00:00Z",
        )

        assert msg.request_id == "req-123"
        assert msg.session_id == "sess-456"
        assert msg.task_id == "task-789"
        assert msg.agent_name == "test-agent"
        assert msg.confidence == 0.75
        assert msg.threshold == 0.80
        assert msg.proposed_action == "Delete all files"
        assert msg.trigger_reason == "Low confidence"
        assert msg.context == {}

    def test_confidence_must_be_between_0_and_1(self) -> None:
        """Test confidence validation (ge=0.0, le=1.0)."""
        with pytest.raises(ValueError):
            ApprovalRequiredMessage(
                request_id="req-123",
                session_id="sess-456",
                task_id="task-789",
                agent_name="test-agent",
                confidence=1.5,  # Invalid: > 1.0
                threshold=0.80,
                proposed_action="Action",
                trigger_reason="Reason",
                requested_at="2025-01-01T00:00:00Z",
            )

    def test_threshold_must_be_between_0_and_1(self) -> None:
        """Test threshold validation (ge=0.0, le=1.0)."""
        with pytest.raises(ValueError):
            ApprovalRequiredMessage(
                request_id="req-123",
                session_id="sess-456",
                task_id="task-789",
                agent_name="test-agent",
                confidence=0.5,
                threshold=-0.1,  # Invalid: < 0.0
                proposed_action="Action",
                trigger_reason="Reason",
                requested_at="2025-01-01T00:00:00Z",
            )

    def test_context_defaults_to_empty_dict(self) -> None:
        """Test context has default empty dict."""
        msg = ApprovalRequiredMessage(
            request_id="req-123",
            session_id="sess-456",
            task_id="task-789",
            agent_name="test-agent",
            confidence=0.5,
            threshold=0.80,
            proposed_action="Action",
            trigger_reason="Reason",
            requested_at="2025-01-01T00:00:00Z",
        )
        assert msg.context == {}

    def test_with_context(self) -> None:
        """Test creating message with custom context."""
        context = {"key": "value", "nested": {"a": 1}}
        msg = ApprovalRequiredMessage(
            request_id="req-123",
            session_id="sess-456",
            task_id="task-789",
            agent_name="test-agent",
            confidence=0.5,
            threshold=0.80,
            proposed_action="Action",
            trigger_reason="Reason",
            context=context,
            requested_at="2025-01-01T00:00:00Z",
        )
        assert msg.context == context


@pytest.mark.unit
@pytest.mark.xdist_group(name="hitl_broadcast")
class TestClarificationRequiredMessage:
    """Tests for ClarificationRequiredMessage model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_valid_message(self) -> None:
        """Test creating a valid ClarificationRequiredMessage."""
        msg = ClarificationRequiredMessage(
            request_id="req-123",
            session_id="sess-456",
            task_id="task-789",
            agent_name="test-agent",
            clarification_type="choice",
            question="Which option do you prefer?",
            requested_at="2025-01-01T00:00:00Z",
        )

        assert msg.request_id == "req-123"
        assert msg.clarification_type == "choice"
        assert msg.question == "Which option do you prefer?"
        assert msg.options == []
        assert msg.placeholder is None
        assert msg.required is True

    def test_with_options(self) -> None:
        """Test creating message with options."""
        options = [
            {"value": "a", "label": "Option A"},
            {"value": "b", "label": "Option B"},
        ]
        msg = ClarificationRequiredMessage(
            request_id="req-123",
            session_id="sess-456",
            task_id="task-789",
            agent_name="test-agent",
            clarification_type="choice",
            question="Choose one",
            options=options,
            requested_at="2025-01-01T00:00:00Z",
        )
        assert msg.options == options

    def test_with_placeholder(self) -> None:
        """Test creating message with placeholder."""
        msg = ClarificationRequiredMessage(
            request_id="req-123",
            session_id="sess-456",
            task_id="task-789",
            agent_name="test-agent",
            clarification_type="text",
            question="Enter your name",
            placeholder="e.g., John Doe",
            requested_at="2025-01-01T00:00:00Z",
        )
        assert msg.placeholder == "e.g., John Doe"

    def test_required_defaults_to_true(self) -> None:
        """Test required field defaults to True."""
        msg = ClarificationRequiredMessage(
            request_id="req-123",
            session_id="sess-456",
            task_id="task-789",
            agent_name="test-agent",
            clarification_type="text",
            question="Question",
            requested_at="2025-01-01T00:00:00Z",
        )
        assert msg.required is True


@pytest.mark.unit
@pytest.mark.xdist_group(name="hitl_broadcast")
class TestApprovalUpdatedMessage:
    """Tests for ApprovalUpdatedMessage model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_approved_message(self) -> None:
        """Test creating an approval message."""
        msg = ApprovalUpdatedMessage(
            request_id="req-123",
            status="approved",
            decided_by="user-123",
            decided_at="2025-01-01T00:00:00Z",
        )
        assert msg.status == "approved"
        assert msg.decided_by == "user-123"
        assert msg.reason is None

    def test_create_rejected_message_with_reason(self) -> None:
        """Test creating a rejection message with reason."""
        msg = ApprovalUpdatedMessage(
            request_id="req-123",
            status="rejected",
            decided_by="admin-1",
            decided_at="2025-01-01T00:00:00Z",
            reason="Action too risky",
        )
        assert msg.status == "rejected"
        assert msg.reason == "Action too risky"


@pytest.mark.unit
@pytest.mark.xdist_group(name="hitl_broadcast")
class TestExecutionResumedMessage:
    """Tests for ExecutionResumedMessage model."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_message(self) -> None:
        """Test creating an ExecutionResumedMessage."""
        msg = ExecutionResumedMessage(
            request_id="req-123",
            task_id="task-789",
            agent_name="test-agent",
            status="approved",
            resumed_at="2025-01-01T00:00:00Z",
        )
        assert msg.request_id == "req-123"
        assert msg.task_id == "task-789"
        assert msg.agent_name == "test-agent"
        assert msg.status == "approved"


# =============================================================================
# WebSocketConnection Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="hitl_broadcast")
class TestWebSocketConnection:
    """Tests for WebSocketConnection class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_connection(self) -> None:
        """Test creating a WebSocketConnection."""
        mock_ws = MagicMock()
        conn = WebSocketConnection(
            websocket=mock_ws,
            session_id="sess-123",
            user_id="user-456",
        )

        assert conn.websocket is mock_ws
        assert conn.session_id == "sess-123"
        assert conn.user_id == "user-456"
        assert isinstance(conn.connected_at, datetime)

    def test_connected_at_is_utc(self) -> None:
        """Test connected_at timestamp is in UTC."""
        mock_ws = MagicMock()
        before = datetime.now(UTC)
        conn = WebSocketConnection(
            websocket=mock_ws,
            session_id="sess-123",
            user_id="user-456",
        )
        after = datetime.now(UTC)

        assert before <= conn.connected_at <= after


# =============================================================================
# AgentRequestBroadcaster Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.xdist_group(name="hitl_broadcast")
class TestAgentRequestBroadcaster:
    """Tests for AgentRequestBroadcaster class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_initial_state(self) -> None:
        """Test broadcaster starts with no connections."""
        broadcaster = AgentRequestBroadcaster()
        assert broadcaster.connection_count == 0

    @pytest.mark.asyncio
    async def test_connect(self) -> None:
        """Test connecting a WebSocket."""
        broadcaster = AgentRequestBroadcaster()
        mock_ws = AsyncMock()

        await broadcaster.connect(mock_ws, "sess-123", "user-456")

        mock_ws.accept.assert_called_once()
        assert broadcaster.connection_count == 1

    @pytest.mark.asyncio
    async def test_connect_multiple(self) -> None:
        """Test connecting multiple WebSockets."""
        broadcaster = AgentRequestBroadcaster()
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()

        await broadcaster.connect(mock_ws1, "sess-1", "user-1")
        await broadcaster.connect(mock_ws2, "sess-2", "user-2")

        assert broadcaster.connection_count == 2

    def test_disconnect(self) -> None:
        """Test disconnecting a WebSocket."""
        broadcaster = AgentRequestBroadcaster()
        mock_ws = MagicMock()
        broadcaster._connections[mock_ws] = WebSocketConnection(websocket=mock_ws, session_id="sess-123", user_id="user-456")

        assert broadcaster.connection_count == 1
        broadcaster.disconnect(mock_ws)
        assert broadcaster.connection_count == 0

    def test_disconnect_unknown_websocket(self) -> None:
        """Test disconnecting an unknown WebSocket does nothing."""
        broadcaster = AgentRequestBroadcaster()
        mock_ws = MagicMock()

        # Should not raise
        broadcaster.disconnect(mock_ws)
        assert broadcaster.connection_count == 0

    @pytest.mark.asyncio
    async def test_broadcast_to_all(self) -> None:
        """Test broadcasting message to all connections."""
        broadcaster = AgentRequestBroadcaster()
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()

        broadcaster._connections[mock_ws1] = WebSocketConnection(websocket=mock_ws1, session_id="sess-1", user_id="user-1")
        broadcaster._connections[mock_ws2] = WebSocketConnection(websocket=mock_ws2, session_id="sess-2", user_id="user-2")

        message = {"type": "test", "data": "hello"}
        await broadcaster.broadcast(message)

        mock_ws1.send_json.assert_called_once_with(message)
        mock_ws2.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_removes_disconnected(self) -> None:
        """Test broadcast removes connections that fail."""
        broadcaster = AgentRequestBroadcaster()
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws2.send_json.side_effect = Exception("Connection closed")

        broadcaster._connections[mock_ws1] = WebSocketConnection(websocket=mock_ws1, session_id="sess-1", user_id="user-1")
        broadcaster._connections[mock_ws2] = WebSocketConnection(websocket=mock_ws2, session_id="sess-2", user_id="user-2")

        await broadcaster.broadcast({"type": "test"})

        # ws1 should remain, ws2 should be removed
        assert broadcaster.connection_count == 1
        assert mock_ws1 in broadcaster._connections
        assert mock_ws2 not in broadcaster._connections

    @pytest.mark.asyncio
    async def test_send_to_session(self) -> None:
        """Test sending message to specific session."""
        broadcaster = AgentRequestBroadcaster()
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws3 = AsyncMock()

        broadcaster._connections[mock_ws1] = WebSocketConnection(websocket=mock_ws1, session_id="sess-A", user_id="user-1")
        broadcaster._connections[mock_ws2] = WebSocketConnection(websocket=mock_ws2, session_id="sess-B", user_id="user-2")
        broadcaster._connections[mock_ws3] = WebSocketConnection(websocket=mock_ws3, session_id="sess-A", user_id="user-3")

        message = {"type": "session-specific"}
        await broadcaster.send_to_session("sess-A", message)

        # Only session-A connections should receive message
        mock_ws1.send_json.assert_called_once_with(message)
        mock_ws2.send_json.assert_not_called()
        mock_ws3.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_to_session_removes_disconnected(self) -> None:
        """Test send_to_session removes failed connections."""
        broadcaster = AgentRequestBroadcaster()
        mock_ws1 = AsyncMock()
        mock_ws1.send_json.side_effect = Exception("Closed")

        broadcaster._connections[mock_ws1] = WebSocketConnection(websocket=mock_ws1, session_id="sess-A", user_id="user-1")

        await broadcaster.send_to_session("sess-A", {"type": "test"})

        assert broadcaster.connection_count == 0

    def test_get_connections_for_session(self) -> None:
        """Test getting all connections for a session."""
        broadcaster = AgentRequestBroadcaster()
        mock_ws1 = MagicMock()
        mock_ws2 = MagicMock()
        mock_ws3 = MagicMock()

        conn1 = WebSocketConnection(websocket=mock_ws1, session_id="sess-A", user_id="user-1")
        conn2 = WebSocketConnection(websocket=mock_ws2, session_id="sess-B", user_id="user-2")
        conn3 = WebSocketConnection(websocket=mock_ws3, session_id="sess-A", user_id="user-3")

        broadcaster._connections[mock_ws1] = conn1
        broadcaster._connections[mock_ws2] = conn2
        broadcaster._connections[mock_ws3] = conn3

        session_a_conns = broadcaster.get_connections_for_session("sess-A")

        assert len(session_a_conns) == 2
        assert conn1 in session_a_conns
        assert conn3 in session_a_conns
        assert conn2 not in session_a_conns

    def test_get_connections_for_nonexistent_session(self) -> None:
        """Test getting connections for a session that has none."""
        broadcaster = AgentRequestBroadcaster()

        connections = broadcaster.get_connections_for_session("nonexistent")
        assert connections == []

    def test_connection_count_property(self) -> None:
        """Test connection_count property."""
        broadcaster = AgentRequestBroadcaster()
        assert broadcaster.connection_count == 0

        mock_ws = MagicMock()
        broadcaster._connections[mock_ws] = WebSocketConnection(websocket=mock_ws, session_id="sess", user_id="user")
        assert broadcaster.connection_count == 1
