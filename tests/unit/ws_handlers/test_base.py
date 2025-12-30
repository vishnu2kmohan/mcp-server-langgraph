"""
WebSocketBase Unit Tests.

TDD tests for the WebSocketBase abstract class that provides
standardized WebSocket infrastructure.
"""

from __future__ import annotations

import asyncio
import gc
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.websockets import WebSocketDisconnect

from mcp_server_langgraph.websocket import (
    AuthUser,
    ConnectionState,
    MessageEnvelope,
    WebSocketConfig,
)

# Import will fail initially (TDD Red phase)
# from mcp_server_langgraph.websocket.base import WebSocketBase

pytestmark = [pytest.mark.unit, pytest.mark.websocket]


@pytest.mark.xdist_group(name="websocket_base")
class TestWebSocketBaseLifecycle:
    """Test WebSocket connection lifecycle management."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_connection_starts_in_connecting_state(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a new WebSocket connection
        WHEN the WebSocketBase is instantiated
        THEN the connection state should be CONNECTING.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test"))
        assert ws.state == ConnectionState.CONNECTING

    @pytest.mark.asyncio
    async def test_run_accepts_websocket_connection(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a WebSocket connection
        WHEN run() is called
        THEN websocket.accept() should be called.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        # Use WebSocketDisconnect which is handled gracefully
        mock_websocket.receive_json = AsyncMock(side_effect=WebSocketDisconnect(code=1000))

        ws = TestWebSocket(config=WebSocketConfig(require_auth=False, endpoint_name="test"))
        await ws.run(mock_websocket)

        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_connect_called_after_auth(self, mock_websocket: MagicMock, sample_user: AuthUser) -> None:
        """
        GIVEN a WebSocket with authentication disabled
        WHEN run() completes authentication
        THEN on_connect() should be called with the user.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        on_connect_called = False
        received_user: AuthUser | None = None

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

            async def on_connect(self, user: AuthUser) -> None:
                nonlocal on_connect_called, received_user
                on_connect_called = True
                received_user = user

        mock_websocket.receive_json = AsyncMock(side_effect=WebSocketDisconnect(code=1000))

        ws = TestWebSocket(config=WebSocketConfig(require_auth=False, endpoint_name="test"))
        await ws.run(mock_websocket)

        assert on_connect_called
        # When auth is disabled, an anonymous user is created
        assert received_user is not None

    @pytest.mark.asyncio
    async def test_on_disconnect_called_on_close(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN an active WebSocket connection
        WHEN the connection closes
        THEN on_disconnect() should be called.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        on_disconnect_called = False

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

            async def on_disconnect(self) -> None:
                nonlocal on_disconnect_called
                on_disconnect_called = True

        mock_websocket.receive_json = AsyncMock(side_effect=WebSocketDisconnect(code=1000))

        ws = TestWebSocket(config=WebSocketConfig(require_auth=False, endpoint_name="test"))

        await ws.run(mock_websocket)

        assert on_disconnect_called


@pytest.mark.xdist_group(name="websocket_base")
class TestWebSocketBaseMessageHandling:
    """Test WebSocket message handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_ping_returns_pong(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN an active WebSocket connection
        WHEN a ping message is received
        THEN a pong response should be sent.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        # First call returns ping, second raises to end loop
        mock_websocket.receive_json = AsyncMock(
            side_effect=[
                {"type": "ping"},
                WebSocketDisconnect(code=1000),
            ]
        )

        ws = TestWebSocket(config=WebSocketConfig(require_auth=False, endpoint_name="test"))

        await ws.run(mock_websocket)

        # Verify pong was sent
        calls = mock_websocket.send_json.call_args_list
        assert len(calls) >= 1
        pong_sent = any(call[0][0].get("type") == "pong" for call in calls)
        assert pong_sent, "Pong response should be sent for ping"

    @pytest.mark.asyncio
    async def test_handle_message_called_for_custom_types(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN an active WebSocket connection
        WHEN a custom message type is received
        THEN handle_message() should be called with the message.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        received_messages: list[MessageEnvelope] = []

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                received_messages.append(message)
                return MessageEnvelope(type="response", payload={"received": True})

        mock_websocket.receive_json = AsyncMock(
            side_effect=[
                {"type": "custom", "payload": {"data": "test"}},
                WebSocketDisconnect(code=1000),
            ]
        )

        ws = TestWebSocket(config=WebSocketConfig(require_auth=False, endpoint_name="test"))

        await ws.run(mock_websocket)

        assert len(received_messages) == 1
        assert received_messages[0].type == "custom"
        assert received_messages[0].payload == {"data": "test"}

    @pytest.mark.asyncio
    async def test_response_sent_when_handler_returns_message(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN an active WebSocket connection
        WHEN handle_message() returns a MessageEnvelope
        THEN the response should be sent to the client.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return MessageEnvelope(
                    type="response",
                    payload={"echo": message.payload},
                    id=message.id,
                )

        mock_websocket.receive_json = AsyncMock(
            side_effect=[
                {"type": "request", "payload": {"key": "value"}, "id": "req-1"},
                WebSocketDisconnect(code=1000),
            ]
        )

        ws = TestWebSocket(config=WebSocketConfig(require_auth=False, endpoint_name="test"))

        await ws.run(mock_websocket)

        # Verify response was sent
        calls = mock_websocket.send_json.call_args_list
        response_sent = any(call[0][0].get("type") == "response" and call[0][0].get("id") == "req-1" for call in calls)
        assert response_sent, "Response should be sent with correlation ID"

    @pytest.mark.asyncio
    async def test_invalid_json_sends_error(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN an active WebSocket connection
        WHEN invalid JSON is received
        THEN an error response should be sent.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        # Simulate JSON decode error by returning non-dict
        mock_websocket.receive_json = AsyncMock(
            side_effect=[
                ValueError("Invalid JSON"),
                WebSocketDisconnect(code=1000),
            ]
        )

        ws = TestWebSocket(config=WebSocketConfig(require_auth=False, endpoint_name="test"))

        await ws.run(mock_websocket)

        # Verify error was sent
        calls = mock_websocket.send_json.call_args_list
        error_sent = any(call[0][0].get("type") == "error" for call in calls)
        assert error_sent, "Error response should be sent for invalid JSON"

    @pytest.mark.asyncio
    async def test_message_timeout_sends_error(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN an active WebSocket connection with short timeout
        WHEN handle_message() takes longer than timeout
        THEN a timeout error should be sent.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class SlowWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                # Simulate slow processing
                await asyncio.sleep(2)  # noqa: sleep-duration
                return MessageEnvelope(type="response")

        mock_websocket.receive_json = AsyncMock(
            side_effect=[
                {"type": "slow_request", "id": "req-123"},
                WebSocketDisconnect(code=1000),
            ]
        )

        # Use a very short timeout for testing
        config = WebSocketConfig(
            require_auth=False,
            endpoint_name="test",
            message_timeout=1,  # 1 second timeout
        )
        ws = SlowWebSocket(config=config)

        await ws.run(mock_websocket)

        # Verify timeout error was sent
        calls = mock_websocket.send_json.call_args_list
        timeout_error_sent = any(
            call[0][0].get("type") == "error" and call[0][0].get("payload", {}).get("code") == "timeout" for call in calls
        )
        assert timeout_error_sent, "Timeout error should be sent when message handling times out"


@pytest.mark.xdist_group(name="websocket_base")
class TestWebSocketBaseAuthentication:
    """Test WebSocket authentication."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_auth_required_closes_without_token(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a WebSocket requiring authentication
        WHEN no token is provided
        THEN connection should be closed with auth error code.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        # Include protocol version to pass version check, but no auth token
        mock_websocket.query_params = {"v": "1.0.0"}
        mock_websocket.headers = {}

        ws = TestWebSocket(config=WebSocketConfig(require_auth=True, endpoint_name="test"))
        await ws.run(mock_websocket)

        mock_websocket.close.assert_called_once()
        close_args = mock_websocket.close.call_args
        # Code 4001 = Authentication required
        # Handle both positional and keyword args for close call
        code = close_args.kwargs.get("code") if close_args.kwargs else None
        if code is None and close_args.args:
            code = close_args.args[0]
        assert code == 4001

    @pytest.mark.asyncio
    async def test_auth_token_from_query_param(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a WebSocket connection
        WHEN token is provided in query params
        THEN token should be extracted and validated.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        # Include protocol version along with token
        mock_websocket.query_params = {"token": "test-jwt-token", "v": "1.0.0"}
        mock_websocket.receive_json = AsyncMock(side_effect=WebSocketDisconnect(code=1000))  # noqa: async-mock-config

        # Mock the auth middleware
        with patch("mcp_server_langgraph.websocket.base.get_auth_middleware_from_websocket") as mock_auth:
            mock_middleware = MagicMock()
            mock_middleware.verify_token = AsyncMock(
                return_value=MagicMock(
                    valid=True,
                    payload={"sub": "test-user", "preferred_username": "testuser"},
                )
            )
            mock_auth.return_value = mock_middleware

            ws = TestWebSocket(config=WebSocketConfig(require_auth=True, endpoint_name="test"))

            await ws.run(mock_websocket)

            mock_middleware.verify_token.assert_called_once_with("test-jwt-token")

    @pytest.mark.asyncio
    async def test_auth_token_from_header(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a WebSocket connection
        WHEN token is provided in Authorization header
        THEN token should be extracted and validated.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        # Include protocol version to pass version check
        mock_websocket.query_params = {"v": "1.0.0"}
        mock_websocket.headers = {"Authorization": "Bearer header-jwt-token"}
        mock_websocket.receive_json = AsyncMock(side_effect=WebSocketDisconnect(code=1000))  # noqa: async-mock-config

        with patch("mcp_server_langgraph.websocket.base.get_auth_middleware_from_websocket") as mock_auth:
            mock_middleware = MagicMock()
            mock_middleware.verify_token = AsyncMock(
                return_value=MagicMock(
                    valid=True,
                    payload={"sub": "test-user", "preferred_username": "testuser"},
                )
            )
            mock_auth.return_value = mock_middleware

            ws = TestWebSocket(config=WebSocketConfig(require_auth=True, endpoint_name="test"))

            await ws.run(mock_websocket)

            mock_middleware.verify_token.assert_called_once_with("header-jwt-token")


@pytest.mark.xdist_group(name="websocket_base")
class TestWebSocketBaseAuthorization:
    """Test WebSocket authorization via OpenFGA."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_authz_check_performed_when_configured(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a WebSocket with OpenFGA authorization configured
        WHEN user authenticates successfully
        THEN OpenFGA check should be performed.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        mock_websocket.query_params = {"token": "test-token", "v": "1.0.0"}
        mock_websocket.receive_json = AsyncMock(side_effect=WebSocketDisconnect(code=1000))

        with (
            patch("mcp_server_langgraph.websocket.base.get_auth_middleware_from_websocket") as mock_auth,
            patch("mcp_server_langgraph.websocket.authz.get_openfga_client") as mock_fga,
        ):
            mock_middleware = MagicMock()
            mock_middleware.verify_token = AsyncMock(
                return_value=MagicMock(
                    valid=True,
                    payload={"sub": "alice", "preferred_username": "alice"},
                )
            )
            mock_auth.return_value = mock_middleware

            mock_fga_client = AsyncMock()  # noqa: async-mock-config
            mock_fga_client.check_permission = AsyncMock(return_value=True)  # noqa: async-mock-config
            mock_fga.return_value = mock_fga_client

            ws = TestWebSocket(
                config=WebSocketConfig(
                    require_auth=True,
                    authz_resource_type="dashboard",
                    authz_resource_id="alerts",
                    authz_required_relation="viewer",
                    endpoint_name="test",
                )
            )

            await ws.run(mock_websocket)

            mock_fga_client.check_permission.assert_called_once()

    @pytest.mark.asyncio
    async def test_authz_denied_closes_connection(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a WebSocket with OpenFGA authorization
        WHEN OpenFGA denies access
        THEN connection should be closed with authz error code.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        mock_websocket.query_params = {"token": "test-token", "v": "1.0.0"}

        with (
            patch("mcp_server_langgraph.websocket.base.get_auth_middleware_from_websocket") as mock_auth,
            patch("mcp_server_langgraph.websocket.authz.get_openfga_client") as mock_fga,
        ):
            mock_middleware = MagicMock()
            mock_middleware.verify_token = AsyncMock(
                return_value=MagicMock(
                    valid=True,
                    payload={"sub": "bob", "preferred_username": "bob"},
                )
            )
            mock_auth.return_value = mock_middleware

            mock_fga_client = AsyncMock()  # noqa: async-mock-config
            mock_fga_client.check_permission = AsyncMock(return_value=False)  # noqa: async-mock-config
            mock_fga.return_value = mock_fga_client

            ws = TestWebSocket(
                config=WebSocketConfig(
                    require_auth=True,
                    authz_resource_type="dashboard",
                    authz_resource_id="alerts",
                    authz_required_relation="admin",
                    authz_fail_closed=True,
                    endpoint_name="test",
                )
            )

            await ws.run(mock_websocket)

            mock_websocket.close.assert_called_once()
            close_args = mock_websocket.close.call_args
            # Code 4003 = Authorization denied
            # Handle both positional and keyword args for close call
            code = close_args.kwargs.get("code") if close_args.kwargs else None
            if code is None and close_args.args:
                code = close_args.args[0]
            assert code == 4003

    @pytest.mark.asyncio
    async def test_authz_fail_closed_on_error(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a WebSocket with fail-closed authorization
        WHEN OpenFGA check fails with an exception
        THEN connection should be closed.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        mock_websocket.query_params = {"token": "test-token", "v": "1.0.0"}

        with (
            patch("mcp_server_langgraph.websocket.base.get_auth_middleware_from_websocket") as mock_auth,
            patch("mcp_server_langgraph.websocket.authz.get_openfga_client") as mock_fga,
        ):
            mock_middleware = MagicMock()
            mock_middleware.verify_token = AsyncMock(
                return_value=MagicMock(
                    valid=True,
                    payload={"sub": "alice", "preferred_username": "alice"},
                )
            )
            mock_auth.return_value = mock_middleware

            mock_fga_client = AsyncMock()  # noqa: async-mock-config
            mock_fga_client.check_permission = AsyncMock(side_effect=Exception("OpenFGA unavailable"))  # noqa: async-mock-config
            mock_fga.return_value = mock_fga_client

            ws = TestWebSocket(
                config=WebSocketConfig(
                    require_auth=True,
                    authz_resource_type="dashboard",
                    authz_resource_id="alerts",
                    authz_required_relation="viewer",
                    authz_fail_closed=True,
                    endpoint_name="test",
                )
            )

            await ws.run(mock_websocket)

            mock_websocket.close.assert_called_once()


@pytest.mark.xdist_group(name="websocket_base")
class TestWebSocketBaseConfig:
    """Test WebSocket configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_config_creates_sensible_defaults(self) -> None:
        """
        GIVEN no custom configuration
        WHEN WebSocketConfig is created
        THEN sensible defaults should be applied.
        """
        config = WebSocketConfig()
        assert config.require_auth is True
        assert config.heartbeat_interval == 30
        assert config.idle_timeout == 1800
        assert config.rate_limit_per_minute == 600
        assert config.max_message_size == 1_000_000
        assert config.authz_fail_closed is True

    def test_config_custom_values(self) -> None:
        """
        GIVEN custom configuration values
        WHEN WebSocketConfig is created
        THEN custom values should override defaults.
        """
        config = WebSocketConfig(
            require_auth=False,
            heartbeat_interval=60,
            rate_limit_per_minute=1000,
            authz_resource_type="workflow",
            authz_required_relation="executor",
        )
        assert config.require_auth is False
        assert config.heartbeat_interval == 60
        assert config.rate_limit_per_minute == 1000
        assert config.authz_resource_type == "workflow"
        assert config.authz_required_relation == "executor"
