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

            mock_fga_client = AsyncMock(return_value=None)  # noqa: async-mock-config
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

            mock_fga_client = AsyncMock(return_value=None)  # noqa: async-mock-config
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

            mock_fga_client = AsyncMock(return_value=None)  # noqa: async-mock-config
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


@pytest.mark.xdist_group(name="websocket_base")
class TestWebSocketBaseContextExtraction:
    """Test WebSocketBase context_id extraction from query parameters.

    These tests verify that WebSocketBase automatically extracts context_id
    and session_id from URL query parameters, making them available to all
    handler subclasses without duplicating extraction logic.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_extracts_context_id_from_query_params(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a WebSocket connection with context_id in query params
        WHEN run() is called and connection established
        THEN _context_id should be populated from query params.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        mock_websocket.query_params = {"v": "1.0.0", "context_id": "ctx-abc-123"}
        mock_websocket.receive_json = AsyncMock(side_effect=WebSocketDisconnect(code=1000))

        ws = TestWebSocket(config=WebSocketConfig(require_auth=False, endpoint_name="test"))
        await ws.run(mock_websocket)

        assert ws.context_id == "ctx-abc-123"

    @pytest.mark.asyncio
    async def test_extracts_session_id_from_query_params(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a WebSocket connection with session_id in query params
        WHEN run() is called and connection established
        THEN _session_id should be populated from query params.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        mock_websocket.query_params = {"v": "1.0.0", "session_id": "sess-xyz-789"}
        mock_websocket.receive_json = AsyncMock(side_effect=WebSocketDisconnect(code=1000))

        ws = TestWebSocket(config=WebSocketConfig(require_auth=False, endpoint_name="test"))
        await ws.run(mock_websocket)

        assert ws.session_id == "sess-xyz-789"

    @pytest.mark.asyncio
    async def test_context_id_takes_precedence_over_session_id(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a WebSocket connection with both context_id and session_id
        WHEN run() is called
        THEN context_id should be accessible as context_id and session_id separately.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        mock_websocket.query_params = {
            "v": "1.0.0",
            "context_id": "ctx-from-url",
            "session_id": "sess-from-url",
        }
        mock_websocket.receive_json = AsyncMock(side_effect=WebSocketDisconnect(code=1000))

        ws = TestWebSocket(config=WebSocketConfig(require_auth=False, endpoint_name="test"))
        await ws.run(mock_websocket)

        # Both should be accessible
        assert ws.context_id == "ctx-from-url"
        assert ws.session_id == "sess-from-url"

    @pytest.mark.asyncio
    async def test_context_id_defaults_to_none(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a WebSocket connection without context_id in query params
        WHEN run() is called
        THEN context_id should be None.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        mock_websocket.query_params = {"v": "1.0.0"}
        mock_websocket.receive_json = AsyncMock(side_effect=WebSocketDisconnect(code=1000))

        ws = TestWebSocket(config=WebSocketConfig(require_auth=False, endpoint_name="test"))
        await ws.run(mock_websocket)

        assert ws.context_id is None
        assert ws.session_id is None

    @pytest.mark.asyncio
    async def test_context_available_in_on_connect(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a WebSocket connection with context_id in query params
        WHEN on_connect() is called
        THEN context_id should be available in the hook.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        context_in_hook: str | None = None

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

            async def on_connect(self, user: AuthUser) -> None:
                nonlocal context_in_hook
                context_in_hook = self.context_id

        mock_websocket.query_params = {"v": "1.0.0", "context_id": "ctx-in-hook"}
        mock_websocket.receive_json = AsyncMock(side_effect=WebSocketDisconnect(code=1000))

        ws = TestWebSocket(config=WebSocketConfig(require_auth=False, endpoint_name="test"))
        await ws.run(mock_websocket)

        assert context_in_hook == "ctx-in-hook"


@pytest.mark.xdist_group(name="websocket_base")
class TestWebSocketBaseUserIdProperty:
    """Test user_id convenience property.

    Many handlers store `self._user_id = user.id` redundantly when the base class
    already has the `_user` object. This property provides convenient access.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_user_id_returns_user_id_when_authenticated(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a WebSocket with authenticated user
        WHEN user_id property is accessed
        THEN it should return the user's ID.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        user_id_in_hook: str | None = None

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

            async def on_connect(self, user: AuthUser) -> None:
                nonlocal user_id_in_hook
                user_id_in_hook = self.user_id

        mock_websocket.query_params = {"v": "1.0.0"}
        mock_websocket.receive_json = AsyncMock(side_effect=WebSocketDisconnect(code=1000))

        ws = TestWebSocket(config=WebSocketConfig(require_auth=False, endpoint_name="test"))
        await ws.run(mock_websocket)

        # Anonymous user has id="anonymous" when auth is disabled
        assert user_id_in_hook == "anonymous"

    @pytest.mark.asyncio
    async def test_user_id_returns_none_before_authentication(self) -> None:
        """
        GIVEN a WebSocket before authentication
        WHEN user_id property is accessed
        THEN it should return None.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(require_auth=False, endpoint_name="test"))

        # Before run() is called, user_id should be None
        assert ws.user_id is None


@pytest.mark.xdist_group(name="websocket_base")
class TestWebSocketBaseErrorHelpers:
    """Test error response helper methods.

    These helpers reduce boilerplate for creating standardized error responses
    that follow the MessageEnvelope pattern.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_error_response_returns_message_envelope(self) -> None:
        """
        GIVEN a WebSocketBase instance
        WHEN create_error_response is called
        THEN it should return a properly formatted MessageEnvelope.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test"))

        response = ws.create_error_response(
            code="validation_failed",
            message="Invalid input data",
            correlation_id="msg-123",
        )

        assert isinstance(response, MessageEnvelope)
        assert response.type == "error"
        assert response.payload["code"] == "validation_failed"
        assert response.payload["message"] == "Invalid input data"
        assert response.id == "msg-123"

    def test_create_error_response_without_correlation_id(self) -> None:
        """
        GIVEN a WebSocketBase instance
        WHEN create_error_response is called without correlation_id
        THEN it should return envelope with None id.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test"))

        response = ws.create_error_response(
            code="server_error",
            message="Something went wrong",
        )

        assert response.type == "error"
        assert response.id is None

    def test_create_unknown_message_error_returns_standardized_error(self) -> None:
        """
        GIVEN a WebSocketBase instance
        WHEN create_unknown_message_error is called
        THEN it should return a standardized "unknown_message_type" error.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test"))

        response = ws.create_unknown_message_error(
            message_type="invalid_action",
            correlation_id="msg-456",
        )

        assert isinstance(response, MessageEnvelope)
        assert response.type == "error"
        assert response.payload["code"] == "unknown_message_type"
        assert "invalid_action" in response.payload["message"]
        assert response.id == "msg-456"

    def test_create_unknown_message_error_usable_in_handle_message(self) -> None:
        """
        GIVEN a handler using create_unknown_message_error
        WHEN handle_message receives unknown type
        THEN it should return the standardized error.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                if message.type == "known_type":
                    return MessageEnvelope(type="success", payload={})
                return self.create_unknown_message_error(message.type, message.id)

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test"))

        # Use asyncio.run since handle_message is async
        import asyncio

        response = asyncio.get_event_loop().run_until_complete(
            ws.handle_message(MessageEnvelope(type="bogus_type", id="req-1"))
        )

        assert response is not None
        assert response.type == "error"
        assert response.payload["code"] == "unknown_message_type"


@pytest.mark.xdist_group(name="websocket_base")
class TestWebSocketBaseSubscriptionHelpers:
    """Test subscription state helpers.

    Many handlers use the pattern `if self._websocket and self._subscribed:`
    before sending messages. These helpers standardize that pattern.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_is_ready_to_send_returns_true_when_connected_and_subscribed(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a connected and subscribed WebSocket handler
        WHEN is_ready_to_send is checked
        THEN it should return True.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test"))
        ws._websocket = mock_websocket
        ws._subscribed = True

        assert ws.is_ready_to_send is True

    @pytest.mark.asyncio
    async def test_is_ready_to_send_returns_false_when_not_subscribed(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a connected but not subscribed WebSocket handler
        WHEN is_ready_to_send is checked
        THEN it should return False.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test"))
        ws._websocket = mock_websocket
        ws._subscribed = False

        assert ws.is_ready_to_send is False

    @pytest.mark.asyncio
    async def test_is_ready_to_send_returns_false_when_no_websocket(self) -> None:
        """
        GIVEN a handler without websocket connection
        WHEN is_ready_to_send is checked
        THEN it should return False.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test"))
        ws._subscribed = True  # Subscribed but no websocket

        assert ws.is_ready_to_send is False

    @pytest.mark.asyncio
    async def test_send_if_subscribed_sends_when_ready(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a connected and subscribed handler
        WHEN send_if_subscribed is called
        THEN it should send the message.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test"))
        ws._websocket = mock_websocket
        ws._subscribed = True

        message = {"type": "test", "payload": {"data": "value"}}
        await ws.send_if_subscribed(message)

        mock_websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_if_subscribed_skips_when_not_ready(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a handler that is not subscribed
        WHEN send_if_subscribed is called
        THEN it should NOT send the message.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test"))
        ws._websocket = mock_websocket
        ws._subscribed = False

        message = {"type": "test", "payload": {"data": "value"}}
        await ws.send_if_subscribed(message)

        mock_websocket.send_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_if_subscribed_returns_true_when_sent(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a connected and subscribed handler
        WHEN send_if_subscribed is called
        THEN it should return True.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test"))
        ws._websocket = mock_websocket
        ws._subscribed = True

        result = await ws.send_if_subscribed({"type": "test"})
        assert result is True

    @pytest.mark.asyncio
    async def test_send_if_subscribed_returns_false_when_not_sent(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a handler that is not subscribed
        WHEN send_if_subscribed is called
        THEN it should return False.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test"))
        ws._websocket = mock_websocket
        ws._subscribed = False

        result = await ws.send_if_subscribed({"type": "test"})
        assert result is False


@pytest.mark.xdist_group(name="websocket_base")
class TestWebSocketBaseSuccessResponseHelper:
    """Test success response helper method.

    This helper creates standardized success responses following the
    MessageEnvelope pattern, complementing create_error_response.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_success_response_returns_message_envelope(self) -> None:
        """
        GIVEN a WebSocketBase instance
        WHEN create_success_response is called
        THEN it should return a properly formatted MessageEnvelope.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test"))

        response = ws.create_success_response(
            type="subscribed",
            payload={"message": "Successfully subscribed"},
            correlation_id="msg-123",
        )

        assert isinstance(response, MessageEnvelope)
        assert response.type == "subscribed"
        assert response.payload["message"] == "Successfully subscribed"
        assert response.id == "msg-123"

    def test_create_success_response_without_correlation_id(self) -> None:
        """
        GIVEN a WebSocketBase instance
        WHEN create_success_response is called without correlation_id
        THEN it should return envelope with None id.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test"))

        response = ws.create_success_response(
            type="data_ready",
            payload={"count": 42},
        )

        assert response.type == "data_ready"
        assert response.payload["count"] == 42
        assert response.id is None

    def test_create_success_response_with_empty_payload(self) -> None:
        """
        GIVEN a WebSocketBase instance
        WHEN create_success_response is called with empty payload
        THEN it should return envelope with empty dict payload.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test"))

        response = ws.create_success_response(
            type="ack",
            payload={},
            correlation_id="req-1",
        )

        assert response.type == "ack"
        assert response.payload == {}
        assert response.id == "req-1"


@pytest.mark.xdist_group(name="websocket_base")
class TestWebSocketBaseLoggingHelpers:
    """Test logging helper methods.

    These helpers standardize connection/disconnection logging
    with consistent format and extra fields.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_log_connected_logs_with_endpoint_and_user(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a connected WebSocket handler
        WHEN log_connected is called
        THEN it should log with endpoint and user_id.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test-endpoint"))
        ws._websocket = mock_websocket
        ws._user = AuthUser(id="user-123", username="testuser")

        with patch("mcp_server_langgraph.websocket.base.logger") as mock_logger:
            ws.log_connected()

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert "test-endpoint" in call_args[0][0]
            assert call_args[1]["extra"]["user_id"] == "user-123"
            assert call_args[1]["extra"]["endpoint"] == "test-endpoint"

    @pytest.mark.asyncio
    async def test_log_connected_with_extra_fields(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a connected WebSocket handler
        WHEN log_connected is called with extra fields
        THEN it should include those fields in the log.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test-endpoint"))
        ws._websocket = mock_websocket
        ws._user = AuthUser(id="user-123", username="testuser")

        with patch("mcp_server_langgraph.websocket.base.logger") as mock_logger:
            ws.log_connected(extra={"session_id": "sess-abc", "custom": "value"})

            call_args = mock_logger.info.call_args
            assert call_args[1]["extra"]["session_id"] == "sess-abc"
            assert call_args[1]["extra"]["custom"] == "value"

    @pytest.mark.asyncio
    async def test_log_disconnected_logs_with_endpoint_and_user(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a WebSocket handler
        WHEN log_disconnected is called
        THEN it should log disconnection with endpoint and user_id.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test-endpoint"))
        ws._user = AuthUser(id="user-456", username="testuser")

        with patch("mcp_server_langgraph.websocket.base.logger") as mock_logger:
            ws.log_disconnected()

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert "disconnected" in call_args[0][0].lower()
            assert call_args[1]["extra"]["user_id"] == "user-456"

    @pytest.mark.asyncio
    async def test_log_disconnected_with_extra_fields(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a WebSocket handler
        WHEN log_disconnected is called with extra fields
        THEN it should include those fields in the log.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test-endpoint"))
        ws._user = AuthUser(id="user-456", username="testuser")

        with patch("mcp_server_langgraph.websocket.base.logger") as mock_logger:
            ws.log_disconnected(extra={"reason": "timeout"})

            call_args = mock_logger.info.call_args
            assert call_args[1]["extra"]["reason"] == "timeout"

    def test_log_connected_handles_no_user(self) -> None:
        """
        GIVEN a WebSocket handler with no authenticated user
        WHEN log_connected is called
        THEN it should log with None user_id.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test-endpoint"))
        # No user set

        with patch("mcp_server_langgraph.websocket.base.logger") as mock_logger:
            ws.log_connected()

            call_args = mock_logger.info.call_args
            assert call_args[1]["extra"]["user_id"] is None


@pytest.mark.xdist_group(name="websocket_base")
class TestWebSocketBaseSubscriptionResponseHelpers:
    """Test subscription response helper methods.

    These helpers create standardized subscribed/unsubscribed responses
    which are the most common response patterns across handlers.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_create_subscribed_response_basic(self) -> None:
        """
        GIVEN a WebSocketBase instance
        WHEN create_subscribed_response is called
        THEN it should return a properly formatted subscribed response.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test"))

        response = ws.create_subscribed_response(correlation_id="msg-123")

        assert isinstance(response, MessageEnvelope)
        assert response.type == "subscribed"
        assert response.payload["message"] == "Successfully subscribed"
        assert response.id == "msg-123"

    def test_create_subscribed_response_with_extra_payload(self) -> None:
        """
        GIVEN a WebSocketBase instance
        WHEN create_subscribed_response is called with extra payload
        THEN it should merge extra payload into the response.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test"))

        response = ws.create_subscribed_response(
            correlation_id="msg-123",
            extra_payload={"connection_id": "conn-abc", "status": "active"},
        )

        assert response.type == "subscribed"
        assert response.payload["message"] == "Successfully subscribed"
        assert response.payload["connection_id"] == "conn-abc"
        assert response.payload["status"] == "active"

    def test_create_subscribed_response_with_custom_message(self) -> None:
        """
        GIVEN a WebSocketBase instance
        WHEN create_subscribed_response is called with custom message
        THEN it should use the custom message.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test"))

        response = ws.create_subscribed_response(
            correlation_id="msg-123",
            message="Subscribed to alerts",
        )

        assert response.payload["message"] == "Subscribed to alerts"

    def test_create_unsubscribed_response_basic(self) -> None:
        """
        GIVEN a WebSocketBase instance
        WHEN create_unsubscribed_response is called
        THEN it should return a properly formatted unsubscribed response.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test"))

        response = ws.create_unsubscribed_response(correlation_id="msg-456")

        assert isinstance(response, MessageEnvelope)
        assert response.type == "unsubscribed"
        assert response.payload["message"] == "Successfully unsubscribed"
        assert response.id == "msg-456"

    def test_create_unsubscribed_response_with_extra_payload(self) -> None:
        """
        GIVEN a WebSocketBase instance
        WHEN create_unsubscribed_response is called with extra payload
        THEN it should merge extra payload into the response.
        """
        from mcp_server_langgraph.websocket.base import WebSocketBase

        class TestWebSocket(WebSocketBase):
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        ws = TestWebSocket(config=WebSocketConfig(endpoint_name="test"))

        response = ws.create_unsubscribed_response(
            correlation_id="msg-456",
            extra_payload={"session_id": "sess-xyz"},
        )

        assert response.type == "unsubscribed"
        assert response.payload["message"] == "Successfully unsubscribed"
        assert response.payload["session_id"] == "sess-xyz"


@pytest.mark.xdist_group(name="websocket_base")
class TestWebSocketBaseBroadcasterMixin:
    """Test BroadcasterMixin for common broadcaster pattern.

    The mixin provides standardized broadcaster integration with:
    - Subscription state management
    - Standard subscribe/unsubscribe methods
    - Automatic cleanup on disconnect
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_broadcaster_mixin_provides_subscribed_property(self) -> None:
        """
        GIVEN a handler using BroadcasterMixin
        WHEN checking subscribed state
        THEN it should have a subscribed property.
        """
        from mcp_server_langgraph.websocket.mixins import BroadcasterMixin

        class TestHandler(BroadcasterMixin):
            pass

        handler = TestHandler()
        assert hasattr(handler, "subscribed")
        assert handler.subscribed is False

    def test_broadcaster_mixin_set_subscribed(self) -> None:
        """
        GIVEN a handler using BroadcasterMixin
        WHEN setting subscribed state
        THEN it should update the state.
        """
        from mcp_server_langgraph.websocket.mixins import BroadcasterMixin

        class TestHandler(BroadcasterMixin):
            pass

        handler = TestHandler()
        handler.subscribed = True
        assert handler.subscribed is True

    @pytest.mark.asyncio
    async def test_broadcaster_mixin_subscribe_calls_broadcaster(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a handler with broadcaster
        WHEN subscribe is called
        THEN it should call broadcaster.subscribe and set subscribed=True.
        """
        from mcp_server_langgraph.websocket.mixins import BroadcasterMixin

        mock_broadcaster = MagicMock()
        mock_broadcaster.subscribe = AsyncMock(return_value=None)

        class TestHandler(BroadcasterMixin):
            def __init__(self) -> None:
                self._broadcaster = mock_broadcaster
                self._websocket = mock_websocket
                super().__init__()

        handler = TestHandler()
        await handler.subscribe()

        mock_broadcaster.subscribe.assert_called_once()
        assert handler.subscribed is True

    @pytest.mark.asyncio
    async def test_broadcaster_mixin_unsubscribe_calls_broadcaster(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a subscribed handler with broadcaster
        WHEN unsubscribe is called
        THEN it should call broadcaster.unsubscribe and set subscribed=False.
        """
        from mcp_server_langgraph.websocket.mixins import BroadcasterMixin

        mock_broadcaster = MagicMock()
        mock_broadcaster.unsubscribe = AsyncMock(return_value=None)

        class TestHandler(BroadcasterMixin):
            def __init__(self) -> None:
                self._broadcaster = mock_broadcaster
                self._websocket = mock_websocket
                self._subscribed = True
                super().__init__()

        handler = TestHandler()
        await handler.unsubscribe()

        mock_broadcaster.unsubscribe.assert_called_once()
        assert handler.subscribed is False

    @pytest.mark.asyncio
    async def test_broadcaster_mixin_unsubscribe_skips_when_not_subscribed(self) -> None:
        """
        GIVEN an unsubscribed handler
        WHEN unsubscribe is called
        THEN it should skip calling broadcaster.
        """
        from mcp_server_langgraph.websocket.mixins import BroadcasterMixin

        mock_broadcaster = MagicMock()
        mock_broadcaster.unsubscribe = AsyncMock(return_value=None)

        class TestHandler(BroadcasterMixin):
            def __init__(self) -> None:
                self._broadcaster = mock_broadcaster
                self._subscribed = False
                super().__init__()

        handler = TestHandler()
        await handler.unsubscribe()

        mock_broadcaster.unsubscribe.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcaster_mixin_subscribe_passes_user_id_kwarg(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a handler using BroadcasterMixin
        WHEN subscribe is called with user_id kwarg
        THEN it should pass user_id to broadcaster.subscribe.
        """
        from mcp_server_langgraph.websocket.mixins import BroadcasterMixin

        mock_broadcaster = MagicMock()
        mock_broadcaster.subscribe = AsyncMock(return_value=None)

        class TestHandler(BroadcasterMixin):
            def __init__(self) -> None:
                self._broadcaster = mock_broadcaster
                self._websocket = mock_websocket
                super().__init__()

        handler = TestHandler()
        await handler.subscribe(user_id="user-123")

        mock_broadcaster.subscribe.assert_called_once_with(mock_websocket, user_id="user-123")
        assert handler.subscribed is True

    @pytest.mark.asyncio
    async def test_broadcaster_mixin_subscribe_passes_multiple_kwargs(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a handler using BroadcasterMixin
        WHEN subscribe is called with multiple kwargs
        THEN it should pass all kwargs to broadcaster.subscribe.
        """
        from mcp_server_langgraph.websocket.mixins import BroadcasterMixin

        mock_broadcaster = MagicMock()
        mock_broadcaster.subscribe = AsyncMock(return_value=None)

        class TestHandler(BroadcasterMixin):
            def __init__(self) -> None:
                self._broadcaster = mock_broadcaster
                self._websocket = mock_websocket
                super().__init__()

        handler = TestHandler()
        await handler.subscribe(user_id="user-123", context_entity_id="ctx-456")

        mock_broadcaster.subscribe.assert_called_once_with(mock_websocket, user_id="user-123", context_entity_id="ctx-456")
        assert handler.subscribed is True

    @pytest.mark.asyncio
    async def test_broadcaster_mixin_subscribe_passes_filter_kwarg(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a handler using BroadcasterMixin
        WHEN subscribe is called with a filter object
        THEN it should pass the filter to broadcaster.subscribe.
        """
        from mcp_server_langgraph.websocket.mixins import BroadcasterMixin

        mock_broadcaster = MagicMock()
        mock_broadcaster.subscribe = AsyncMock(return_value=None)
        test_filter = {"service_name": "test", "status": "OK"}

        class TestHandler(BroadcasterMixin):
            def __init__(self) -> None:
                self._broadcaster = mock_broadcaster
                self._websocket = mock_websocket
                super().__init__()

        handler = TestHandler()
        await handler.subscribe(filter_=test_filter)

        mock_broadcaster.subscribe.assert_called_once_with(mock_websocket, filter_=test_filter)
        assert handler.subscribed is True

    @pytest.mark.asyncio
    async def test_broadcaster_mixin_subscribe_no_kwargs_still_works(self, mock_websocket: MagicMock) -> None:
        """
        GIVEN a handler using BroadcasterMixin
        WHEN subscribe is called without kwargs (backwards compatible)
        THEN it should call broadcaster.subscribe with just websocket.
        """
        from mcp_server_langgraph.websocket.mixins import BroadcasterMixin

        mock_broadcaster = MagicMock()
        mock_broadcaster.subscribe = AsyncMock(return_value=None)

        class TestHandler(BroadcasterMixin):
            def __init__(self) -> None:
                self._broadcaster = mock_broadcaster
                self._websocket = mock_websocket
                super().__init__()

        handler = TestHandler()
        await handler.subscribe()

        mock_broadcaster.subscribe.assert_called_once_with(mock_websocket)
        assert handler.subscribed is True
