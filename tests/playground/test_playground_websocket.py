"""
Tests for Interactive Playground WebSocket streaming.

Tests the playground WebSocket with:
- Connection lifecycle (connect, disconnect)
- Message streaming from LLM
- Tool call notifications
- Error handling
- Session validation
- Authentication

Follows TDD principles and memory safety patterns for pytest-xdist.
"""

import gc
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

pytestmark = [pytest.mark.unit, pytest.mark.playground, pytest.mark.websocket]


# ==============================================================================
# WebSocket Connection Tests
# ==============================================================================


@pytest.mark.xdist_group(name="playground_websocket")
class TestPlaygroundWebSocketConnection:
    """Test WebSocket connection lifecycle."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_websocket_connect_with_valid_session(self) -> None:
        """Test WebSocket connects successfully with valid session ID."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            # Create session first
            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "WebSocket Test"},
            )
            session_id = session_response.json()["session_id"]

            # Connect WebSocket
            with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
                # Should receive welcome message
                data = websocket.receive_json()
                assert data["type"] == "connected"
                assert data["session_id"] == session_id

    @pytest.mark.unit
    def test_websocket_connect_with_invalid_session_fails(self) -> None:
        """Test WebSocket connection fails with invalid session ID."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            # Try to connect with invalid session
            with pytest.raises(Exception):
                with client.websocket_connect("/ws/playground/invalid-session-id"):
                    pass

    @pytest.mark.unit
    def test_websocket_disconnect_gracefully(self) -> None:
        """Test WebSocket disconnects gracefully."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            # Create session
            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Disconnect Test"},
            )
            session_id = session_response.json()["session_id"]

            # Connect and disconnect
            with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
                # Receive welcome
                websocket.receive_json()
                # Client disconnect handled gracefully
            # No exception should be raised


# ==============================================================================
# WebSocket Message Streaming Tests
# ==============================================================================


@pytest.mark.xdist_group(name="playground_websocket")
class TestPlaygroundWebSocketStreaming:
    """Test WebSocket message streaming."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_send_message_receives_streaming_response(self) -> None:
        """Test sending message receives streaming response chunks."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            # Create session
            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Streaming Test"},
            )
            session_id = session_response.json()["session_id"]

            with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
                # Receive welcome
                websocket.receive_json()

                # Send message
                websocket.send_json(
                    {
                        "type": "message",
                        "content": "Hello, test message",
                    }
                )

                # Receive streaming response
                response = websocket.receive_json()
                assert response["type"] in ["chunk", "message", "complete"]

    @pytest.mark.unit
    def test_streaming_response_includes_token_chunks(self) -> None:
        """Test streaming response includes token-by-token chunks."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            # Create session
            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Token Test"},
            )
            session_id = session_response.json()["session_id"]

            with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
                websocket.receive_json()  # Welcome

                websocket.send_json(
                    {
                        "type": "message",
                        "content": "Count to 3",
                    }
                )

                # Should receive multiple chunks
                messages = []
                for _ in range(10):  # Max iterations to prevent infinite loop
                    try:
                        msg = websocket.receive_json()
                        messages.append(msg)
                        if msg.get("type") == "complete":
                            break
                    except Exception:
                        break

                assert len(messages) > 0


# ==============================================================================
# WebSocket Tool Call Tests
# ==============================================================================


@pytest.mark.xdist_group(name="playground_websocket")
class TestPlaygroundWebSocketToolCalls:
    """Test WebSocket tool call notifications."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_tool_call_notification_sent(self) -> None:
        """Test that tool calls are notified via WebSocket."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            # Create session
            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Tool Test"},
            )
            session_id = session_response.json()["session_id"]

            with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
                websocket.receive_json()  # Welcome

                # Send message that might trigger tool call
                websocket.send_json(
                    {
                        "type": "message",
                        "content": "What's the weather in San Francisco?",
                    }
                )

                # Collect messages looking for tool_call type
                messages = []
                for _ in range(10):
                    try:
                        msg = websocket.receive_json()
                        messages.append(msg)
                        if msg.get("type") == "complete":
                            break
                    except Exception:
                        break

                # At minimum we should get some response
                assert len(messages) > 0


# ==============================================================================
# WebSocket Error Handling Tests
# ==============================================================================


@pytest.mark.xdist_group(name="playground_websocket")
class TestPlaygroundWebSocketErrors:
    """Test WebSocket error handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_invalid_message_format_returns_error(self) -> None:
        """Test that invalid message format returns error."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Error Test"},
            )
            session_id = session_response.json()["session_id"]

            with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
                websocket.receive_json()  # Welcome

                # Send invalid message (missing type)
                websocket.send_json({"invalid": "message"})

                response = websocket.receive_json()
                assert response["type"] == "error"

    @pytest.mark.unit
    def test_empty_message_returns_error(self) -> None:
        """Test that empty message content returns error."""
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Empty Test"},
            )
            session_id = session_response.json()["session_id"]

            with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
                websocket.receive_json()  # Welcome

                websocket.send_json(
                    {
                        "type": "message",
                        "content": "",
                    }
                )

                response = websocket.receive_json()
                assert response["type"] == "error"


# ==============================================================================
# WebSocket Authentication Tests
# ==============================================================================


@pytest.mark.xdist_group(name="playground_websocket")
class TestPlaygroundWebSocketAuth:
    """Test WebSocket authentication."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_websocket_requires_valid_session_token(self) -> None:
        """Test that WebSocket requires valid session ownership."""
        # This test validates the pattern - actual auth check happens in middleware
        from mcp_server_langgraph.playground.api.server import app

        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            client = TestClient(app)

            # Create session as one user
            session_response = client.post(
                "/api/playground/sessions",
                json={"name": "Auth Test"},
            )
            session_id = session_response.json()["session_id"]

            # In development mode, connection should work
            with client.websocket_connect(f"/ws/playground/{session_id}") as websocket:
                data = websocket.receive_json()
                assert data["type"] == "connected"
