"""
WebSocket Protocol Version Integration Tests.

Integration tests for WebSocket protocol version validation.
Tests the end-to-end flow of protocol version checking through WebSocketBase.

TDD RED phase: These tests define the expected behavior for protocol version
validation at the WebSocket endpoint level.
"""

from __future__ import annotations

import gc

import pytest
from fastapi import FastAPI, WebSocket
from starlette.testclient import TestClient

from mcp_server_langgraph.websocket.base import WebSocketBase
from mcp_server_langgraph.websocket.protocols import PROTOCOL_VERSION
from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

pytestmark = [
    pytest.mark.integration,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="websocket_protocol_version_integration"),
]


class ProtocolVersionTestHandler(WebSocketBase):
    """Test WebSocket handler for protocol version testing."""

    def __init__(self, validate_protocol: bool = True):
        config = WebSocketConfig(
            endpoint_name="protocol-test",
            require_auth=False,  # No auth to focus on protocol version
            validate_protocol_version=validate_protocol,
            heartbeat_interval=30,
        )
        super().__init__(config)

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        """Echo messages back."""
        if message.type == "echo":
            return MessageEnvelope(
                type="echo_response",
                payload={"echo": message.payload},
            )
        return None


@pytest.fixture
def protocol_version_app() -> FastAPI:
    """Create a test FastAPI app with protocol version validation endpoint."""
    app = FastAPI()

    @app.websocket("/ws/protocol-required")
    async def protocol_required_websocket(websocket: WebSocket):
        """WebSocket endpoint with protocol version validation enabled."""
        handler = ProtocolVersionTestHandler(validate_protocol=True)
        await handler.run(websocket)

    @app.websocket("/ws/protocol-optional")
    async def protocol_optional_websocket(websocket: WebSocket):
        """WebSocket endpoint with protocol version validation disabled."""
        handler = ProtocolVersionTestHandler(validate_protocol=False)
        await handler.run(websocket)

    return app


class TestProtocolVersionRequired:
    """Integration tests for WebSocket endpoints with protocol version required."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_connection_without_version_closes_immediately(
        self,
        protocol_version_app: FastAPI,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Connection without ?v= param should close with protocol version error."""
        client = TestClient(protocol_version_app)

        with client.websocket_connect("/ws/protocol-required") as websocket:
            # Try to receive - should fail as server closed connection
            try:
                websocket.receive_json(timeout=2)
                pytest.fail("Expected WebSocket to close due to protocol version")
            except Exception:
                pass  # Expected - connection closed

        # Verify log message shows protocol version error
        assert "Protocol version mismatch" in caplog.text
        assert "Missing protocol version" in caplog.text

    def test_connection_with_invalid_version_format_closes(
        self,
        protocol_version_app: FastAPI,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Connection with invalid version format should close."""
        client = TestClient(protocol_version_app)

        with client.websocket_connect("/ws/protocol-required?v=invalid") as websocket:
            try:
                websocket.receive_json(timeout=2)
                pytest.fail("Expected WebSocket to close due to invalid version format")
            except Exception:
                pass  # Expected - connection closed

        assert "Protocol version mismatch" in caplog.text
        assert "Invalid protocol version format" in caplog.text

    def test_connection_with_incompatible_major_version_closes(
        self,
        protocol_version_app: FastAPI,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Connection with incompatible major version should close."""
        client = TestClient(protocol_version_app)

        with client.websocket_connect("/ws/protocol-required?v=99.0.0") as websocket:
            try:
                websocket.receive_json(timeout=2)
                pytest.fail("Expected WebSocket to close due to incompatible version")
            except Exception:
                pass  # Expected - connection closed

        assert "Protocol version mismatch" in caplog.text
        assert "Client: 99.0.0" in caplog.text

    def test_connection_with_compatible_version_succeeds(
        self,
        protocol_version_app: FastAPI,
    ) -> None:
        """Connection with compatible version should succeed."""
        client = TestClient(protocol_version_app)

        # Use current protocol version
        with client.websocket_connect(f"/ws/protocol-required?v={PROTOCOL_VERSION}") as ws:
            # Send a test message
            ws.send_json({"type": "echo", "payload": {"test": "data"}})
            response = ws.receive_json()

            assert response["type"] == "echo_response"
            assert response["payload"]["echo"]["test"] == "data"

    def test_connection_with_older_compatible_minor_version_succeeds(
        self,
        protocol_version_app: FastAPI,
    ) -> None:
        """Connection with older compatible minor version should succeed."""
        client = TestClient(protocol_version_app)

        # Use older minor version (1.0.0 should be compatible with 1.x.x)
        with client.websocket_connect("/ws/protocol-required?v=1.0.0") as ws:
            ws.send_json({"type": "echo", "payload": {"test": "minor"}})
            response = ws.receive_json()

            assert response["type"] == "echo_response"

    def test_connection_with_higher_minor_version_closes(
        self,
        protocol_version_app: FastAPI,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Connection with higher minor version should close."""
        client = TestClient(protocol_version_app)

        # Use higher minor version (1.99.0 requires server >=1.99.0)
        with client.websocket_connect("/ws/protocol-required?v=1.99.0") as websocket:
            try:
                websocket.receive_json(timeout=2)
                pytest.fail("Expected WebSocket to close due to higher minor version")
            except Exception:
                pass  # Expected - connection closed

        assert "Protocol version mismatch" in caplog.text
        assert "Client: 1.99.0" in caplog.text

    def test_patch_version_difference_is_ignored(
        self,
        protocol_version_app: FastAPI,
    ) -> None:
        """Patch version differences should not affect compatibility."""
        client = TestClient(protocol_version_app)

        # Use different patch version
        with client.websocket_connect("/ws/protocol-required?v=1.0.99") as ws:
            ws.send_json({"type": "echo", "payload": {"test": "patch"}})
            response = ws.receive_json()

            assert response["type"] == "echo_response"


class TestProtocolVersionOptional:
    """Integration tests for WebSocket endpoints with protocol version optional."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_connection_without_version_succeeds_when_disabled(
        self,
        protocol_version_app: FastAPI,
    ) -> None:
        """Connection without ?v= should succeed when validation is disabled."""
        client = TestClient(protocol_version_app)

        with client.websocket_connect("/ws/protocol-optional") as ws:
            ws.send_json({"type": "echo", "payload": {"test": "no-version"}})
            response = ws.receive_json()

            assert response["type"] == "echo_response"
            assert response["payload"]["echo"]["test"] == "no-version"

    def test_connection_with_any_version_succeeds_when_disabled(
        self,
        protocol_version_app: FastAPI,
    ) -> None:
        """Connection with any version should succeed when validation disabled."""
        client = TestClient(protocol_version_app)

        with client.websocket_connect("/ws/protocol-optional?v=99.99.99") as ws:
            ws.send_json({"type": "echo", "payload": {"test": "any-version"}})
            response = ws.receive_json()

            assert response["type"] == "echo_response"


class TestProtocolVersionErrorDetails:
    """Integration tests for protocol version error message details."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_missing_version_error_suggests_query_param(
        self,
        protocol_version_app: FastAPI,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Missing version error should suggest adding ?v= query param."""
        client = TestClient(protocol_version_app)

        with client.websocket_connect("/ws/protocol-required") as websocket:
            try:
                websocket.receive_json(timeout=2)
            except Exception:
                pass

        # Error message should contain helpful guidance
        assert "Add ?v=1.0.0" in caplog.text

    def test_incompatible_version_error_shows_versions(
        self,
        protocol_version_app: FastAPI,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Incompatible version error should show client and server versions."""
        client = TestClient(protocol_version_app)

        with client.websocket_connect("/ws/protocol-required?v=2.0.0") as websocket:
            try:
                websocket.receive_json(timeout=2)
            except Exception:
                pass

        # Should show both client and server versions
        assert "Client: 2.0.0" in caplog.text
        assert f"Server: {PROTOCOL_VERSION}" in caplog.text
