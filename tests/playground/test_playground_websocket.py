"""
Playground WebSocket Tests (TDD Red Phase)

Tests for WebSocket streaming functionality in the Interactive Playground.
Following TDD: These tests are written BEFORE the implementation.

Test Coverage:
- WebSocket connection lifecycle
- Message streaming
- Error handling
- Connection cancellation
"""

import gc

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

# Mark all tests in this module for xdist memory safety
pytestmark = [
    pytest.mark.unit,
    pytest.mark.playground,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="playground_websocket"),
]


class TestWebSocketConnection:
    """Tests for WebSocket connection handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_connect_requires_session_id(self) -> None:
        """WebSocket connection should require a valid session_id in path."""
        from mcp_server_langgraph.playground.api.server import app

        client = TestClient(app)

        # Connect without session_id should fail
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/playground/"):
                pass

    def test_websocket_connect_with_valid_session(self) -> None:
        """WebSocket should connect successfully with valid session_id."""
        from mcp_server_langgraph.playground.api.server import app

        client = TestClient(app)
        session_id = "test-session-123"

        with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
            # Connection should be established
            # Server should send initial connection acknowledgment
            data = websocket.receive_json()
            assert data["type"] == "connection_ack"
            assert data["session_id"] == session_id

    def test_websocket_rejects_invalid_session(self) -> None:
        """WebSocket should reject connection for non-existent session."""
        from mcp_server_langgraph.playground.api.server import app

        client = TestClient(app)
        session_id = "nonexistent-session-999"

        # Should close with error for invalid session
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/ws/playground/{session_id}"):
                pass

        assert exc_info.value.code in [1008, 4004]  # Policy violation or custom error


class TestWebSocketMessaging:
    """Tests for WebSocket message handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_send_message_receives_streaming_response(self) -> None:
        """Sending a message should receive streaming token response."""
        from mcp_server_langgraph.playground.api.server import app

        client = TestClient(app)
        session_id = "test-session-123"

        with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
            # Skip connection ack
            websocket.receive_json()

            # Send a message
            websocket.send_json(
                {
                    "type": "message",
                    "content": "Hello, agent!",
                }
            )

            # Should receive streaming tokens
            responses = []
            for _ in range(10):  # Read up to 10 messages
                try:
                    data = websocket.receive_json(timeout=1.0)
                    responses.append(data)
                    if data.get("type") == "message_end":
                        break
                except Exception:
                    break

            # Should have received at least start and end messages
            assert any(r.get("type") == "message_start" for r in responses)
            assert any(r.get("type") in ["message_end", "token"] for r in responses)

    def test_message_includes_metadata(self) -> None:
        """Streaming messages should include metadata (timestamp, message_id)."""
        from mcp_server_langgraph.playground.api.server import app

        client = TestClient(app)
        session_id = "test-session-123"

        with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
            websocket.receive_json()  # Skip ack

            websocket.send_json(
                {
                    "type": "message",
                    "content": "Test message",
                }
            )

            data = websocket.receive_json(timeout=5.0)
            assert "message_id" in data or "timestamp" in data


class TestWebSocketCancellation:
    """Tests for message cancellation via WebSocket."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_cancel_message_stops_streaming(self) -> None:
        """Sending cancel should stop ongoing message streaming."""
        from mcp_server_langgraph.playground.api.server import app

        client = TestClient(app)
        session_id = "test-session-123"

        with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
            websocket.receive_json()  # Skip ack

            # Send a message
            websocket.send_json(
                {
                    "type": "message",
                    "content": "Tell me a long story...",
                }
            )

            # Wait for streaming to start
            start_msg = websocket.receive_json(timeout=5.0)
            assert start_msg.get("type") == "message_start"

            # Send cancel
            websocket.send_json({"type": "cancel"})

            # Should receive cancellation acknowledgment
            responses = []
            for _ in range(5):
                try:
                    data = websocket.receive_json(timeout=1.0)
                    responses.append(data)
                    if data.get("type") in ["cancelled", "message_end"]:
                        break
                except Exception:
                    break

            assert any(r.get("type") in ["cancelled", "message_end"] for r in responses)


class TestWebSocketErrors:
    """Tests for WebSocket error handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_invalid_message_format_returns_error(self) -> None:
        """Sending invalid JSON should return error message."""
        from mcp_server_langgraph.playground.api.server import app

        client = TestClient(app)
        session_id = "test-session-123"

        with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
            websocket.receive_json()  # Skip ack

            # Send malformed message
            websocket.send_json({"invalid": "message"})  # Missing 'type'

            data = websocket.receive_json(timeout=5.0)
            assert data.get("type") == "error"
            assert "message" in data

    def test_unknown_message_type_returns_error(self) -> None:
        """Unknown message type should return error."""
        from mcp_server_langgraph.playground.api.server import app

        client = TestClient(app)
        session_id = "test-session-123"

        with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
            websocket.receive_json()  # Skip ack

            websocket.send_json({"type": "unknown_type"})

            data = websocket.receive_json(timeout=5.0)
            assert data.get("type") == "error"


class TestWebSocketHeartbeat:
    """Tests for WebSocket heartbeat/ping handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ping_receives_pong(self) -> None:
        """Sending ping should receive pong response."""
        from mcp_server_langgraph.playground.api.server import app

        client = TestClient(app)
        session_id = "test-session-123"

        with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
            websocket.receive_json()  # Skip ack

            websocket.send_json({"type": "ping"})

            data = websocket.receive_json(timeout=5.0)
            assert data.get("type") == "pong"
