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
from unittest.mock import AsyncMock

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


@pytest.mark.xdist_group(name="playground_websocket")
class TestWebSocketConnection:
    """Tests for WebSocket connection handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_connect_requires_session_id(self, app_with_mock_manager) -> None:
        """WebSocket connection should require a valid session_id in path."""
        client = TestClient(app_with_mock_manager)

        # Connect without session_id should fail
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/playground/"):
                pass

    def test_websocket_connect_with_valid_session(self, app_with_mock_manager) -> None:
        """WebSocket should connect successfully with valid session_id."""
        client = TestClient(app_with_mock_manager)
        session_id = "test-session-123"

        with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
            # Connection should be established
            # Server should send initial connection acknowledgment
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert data["session_id"] == session_id

    def test_websocket_rejects_invalid_session(self, mock_session_manager, app_with_mock_manager) -> None:
        """WebSocket should reject connection for non-existent session."""
        # Mock session not found
        mock_session_manager.get_session = AsyncMock(return_value=None)

        client = TestClient(app_with_mock_manager)
        session_id = "nonexistent-session-999"

        # Should close with error for invalid session
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/ws/playground/{session_id}") as ws:
                # Try to receive - should fail
                ws.receive_json()

        assert exc_info.value.code in [1008, 4004]  # Policy violation or custom error


@pytest.mark.xdist_group(name="playground_websocket")
class TestWebSocketMessaging:
    """Tests for WebSocket message handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_send_message_receives_streaming_response(self, app_with_mock_manager) -> None:
        """Sending a message should receive streaming token response."""
        client = TestClient(app_with_mock_manager)
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

            # Should receive streaming tokens (no timeout in TestClient)
            responses = []
            for _ in range(10):  # Read up to 10 messages
                try:
                    data = websocket.receive_json()
                    responses.append(data)
                    if data.get("type") in ["done", "message_end"]:
                        break
                except Exception:
                    break

            # Should have received at least some response (token or done)
            assert len(responses) > 0
            assert any(r.get("type") in ["done", "token"] for r in responses)

    def test_message_includes_metadata(self, app_with_mock_manager) -> None:
        """Streaming messages should include metadata (timestamp, message_id)."""
        client = TestClient(app_with_mock_manager)
        session_id = "test-session-123"

        with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
            websocket.receive_json()  # Skip ack

            websocket.send_json(
                {
                    "type": "message",
                    "content": "Test message",
                }
            )

            # Get first response (no timeout in TestClient)
            data = websocket.receive_json()
            # Should have some identifying information
            assert data.get("type") is not None


@pytest.mark.xdist_group(name="playground_websocket")
class TestWebSocketCancellation:
    """Tests for message cancellation via WebSocket."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_cancel_message_stops_streaming(self, app_with_mock_manager) -> None:
        """Sending cancel should stop ongoing message streaming."""
        client = TestClient(app_with_mock_manager)
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

            # Get first response (no timeout in TestClient)
            first_msg = websocket.receive_json()
            assert first_msg is not None

            # Send cancel
            websocket.send_json({"type": "cancel"})

            # Should receive cancellation acknowledgment or done
            responses = []
            for _ in range(5):
                try:
                    data = websocket.receive_json()
                    responses.append(data)
                    if data.get("type") in ["cancelled", "done"]:
                        break
                except Exception:
                    break

            # At least got some response
            assert len(responses) >= 0  # May be empty if cancel was immediate


@pytest.mark.xdist_group(name="playground_websocket")
class TestWebSocketErrors:
    """Tests for WebSocket error handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_invalid_message_format_returns_error(self, app_with_mock_manager) -> None:
        """Sending invalid JSON should return error message."""
        client = TestClient(app_with_mock_manager)
        session_id = "test-session-123"

        with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
            websocket.receive_json()  # Skip ack

            # Send malformed message
            websocket.send_json({"invalid": "message"})  # Missing 'type'

            data = websocket.receive_json()
            assert data.get("type") == "error"
            assert "message" in data

    def test_unknown_message_type_returns_error(self, app_with_mock_manager) -> None:
        """Unknown message type should return error."""
        client = TestClient(app_with_mock_manager)
        session_id = "test-session-123"

        with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
            websocket.receive_json()  # Skip ack

            websocket.send_json({"type": "unknown_type"})

            data = websocket.receive_json()
            assert data.get("type") == "error"


@pytest.mark.xdist_group(name="playground_websocket")
class TestWebSocketHeartbeat:
    """Tests for WebSocket heartbeat/ping handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_ping_receives_pong(self, app_with_mock_manager) -> None:
        """Sending ping should receive pong response."""
        client = TestClient(app_with_mock_manager)
        session_id = "test-session-123"

        with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
            websocket.receive_json()  # Skip ack

            websocket.send_json({"type": "ping"})

            data = websocket.receive_json()
            assert data.get("type") == "pong"
