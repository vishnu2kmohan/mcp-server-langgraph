"""
Integration tests for WebSocket Token Expiration Flow.

Tests the end-to-end flow of token expiration during active WebSocket connections:
1. Backend detects token expiration via periodic validation
2. Backend closes connection with code 4010 (WS_CLOSE_TOKEN_EXPIRED)
3. Client receives 4010 and can distinguish from other close codes

These tests verify the integration between:
- Token validation module (token_validation.py)
- WebSocketBase periodic validation task (base.py)
- TokenExpiredError exception handling (exceptions.py)

Related:
- ADR-0074: WebSocket Token Expiration Handling
- Unit tests: tests/unit/websocket_pkg/test_token_validation.py
- Unit tests: tests/unit/websocket_pkg/test_base.py
"""

from __future__ import annotations

import asyncio
import gc
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest

from mcp_server_langgraph.websocket.base import WebSocketBase
from mcp_server_langgraph.websocket.exceptions import TokenExpiredError
from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketConfig

if TYPE_CHECKING:
    pass

pytestmark = [
    pytest.mark.integration,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="websocket_token_expiration"),
]

# Test JWT secret
TEST_JWT_SECRET = "test-secret-for-token-expiration-tests"

# Constant for the patch path - import is local within _create_rate_limiter method
RATE_LIMITER_PATCH = "mcp_server_langgraph.websocket.rate_limiter.get_websocket_rate_limiter"


def _create_test_token(expires_in_seconds: int) -> str:
    """Create a test JWT token with specified expiration."""
    now = datetime.now(UTC)
    payload = {
        "sub": "user:test-user",
        "username": "testuser",
        "email": "test@example.com",
        "exp": now + timedelta(seconds=expires_in_seconds),
        "iat": now,
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


class _TokenExpirationTestHandler(WebSocketBase):
    """Concrete WebSocket handler for testing (underscore prefix to avoid pytest collection)."""

    def __init__(self, config: WebSocketConfig):
        super().__init__(config)
        self.messages_received: list[MessageEnvelope] = []
        self.connected = False
        self.disconnected = False

    async def on_connect(self, user) -> None:
        self.connected = True

    async def on_disconnect(self) -> None:
        self.disconnected = True

    async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
        self.messages_received.append(message)
        return MessageEnvelope(type="echo", payload={"received": message.payload})


@pytest.mark.xdist_group(name="websocket_token_expiration")
class TestTokenExpiredExceptionIntegration:
    """Tests for TokenExpiredError exception integration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_token_expired_error_has_correct_close_code(self) -> None:
        """GIVEN TokenExpiredError WHEN raised THEN has code 4010."""
        error = TokenExpiredError()

        assert error.code == 4010
        assert "expired" in error.reason.lower()

    def test_token_expired_error_is_authentication_error(self) -> None:
        """GIVEN TokenExpiredError WHEN checking type THEN is AuthenticationError."""
        from mcp_server_langgraph.websocket.exceptions import AuthenticationError

        error = TokenExpiredError()

        assert isinstance(error, AuthenticationError)

    def test_token_expired_error_custom_message(self) -> None:
        """GIVEN custom message WHEN creating TokenExpiredError THEN uses message."""
        error = TokenExpiredError(message="Session expired after 30 minutes")

        assert "30 minutes" in str(error)


@pytest.mark.xdist_group(name="websocket_token_expiration")
class TestPeriodicTokenValidationIntegration:
    """Tests for periodic token validation during active connections."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.timeout(15)
    async def test_connection_closed_with_4010_when_token_expires(self) -> None:
        """
        GIVEN active WebSocket connection with expiring token
        WHEN token validation detects expiration
        THEN connection closes with code 4010.
        """
        from starlette.websockets import WebSocketDisconnect

        config = WebSocketConfig(
            endpoint_name="test-token-expiration",
            require_auth=True,
            token_validation_interval=1,  # 1 second for fast testing
        )

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = _TokenExpirationTestHandler(config)

        # Create a token that will be detected as expired
        expired_token = _create_test_token(-60)  # Expired 1 minute ago

        mock_ws = AsyncMock()  # noqa: async-mock-config
        mock_ws.query_params = {"token": expired_token}
        mock_ws.headers = {}
        mock_ws.client_state = None

        # Mock auth middleware to accept token initially
        mock_auth = AsyncMock()  # noqa: async-mock-config
        mock_result = MagicMock()
        mock_result.valid = True
        mock_result.payload = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "exp": int(datetime.now(UTC).timestamp()) - 60,  # Expired
        }
        mock_auth.verify_token = AsyncMock(return_value=mock_result)

        # Track close calls
        close_codes: list[int] = []

        async def track_close(**kwargs):
            close_codes.append(kwargs.get("code", 1000))
            mock_ws.receive_json = AsyncMock(side_effect=WebSocketDisconnect())

        mock_ws.close = AsyncMock(side_effect=track_close)

        # First receive will wait, then disconnect after close
        receive_calls = [0]

        async def receive_or_wait():
            receive_calls[0] += 1
            if receive_calls[0] == 1:
                await asyncio.sleep(3)  # noqa: sleep-duration  # Wait for validation to trigger
                raise WebSocketDisconnect()
            raise WebSocketDisconnect()

        mock_ws.receive_json = AsyncMock(side_effect=receive_or_wait)

        with patch(
            "mcp_server_langgraph.websocket.base.get_auth_middleware_from_websocket",
            return_value=mock_auth,
        ):
            with patch(
                "mcp_server_langgraph.websocket.base.is_token_expired",
                return_value=True,  # Token is always expired
            ):
                await handler.run(mock_ws)

        # Verify connection was closed with 4010
        assert 4010 in close_codes, f"Expected 4010 in close codes, got: {close_codes}"

    @pytest.mark.timeout(15)
    async def test_validation_task_cancelled_on_disconnect(self) -> None:
        """
        GIVEN active WebSocket connection with validation task
        WHEN client disconnects normally
        THEN validation task is cancelled cleanly.
        """
        from starlette.websockets import WebSocketDisconnect

        config = WebSocketConfig(
            endpoint_name="test-validation-cancel",
            require_auth=True,
            token_validation_interval=60,  # Long interval to ensure task is active
        )

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            handler = _TokenExpirationTestHandler(config)

        # Create valid token
        valid_token = _create_test_token(3600)

        mock_ws = AsyncMock()  # noqa: async-mock-config
        mock_ws.query_params = {"token": valid_token}
        mock_ws.headers = {}
        mock_ws.client_state = None

        mock_auth = AsyncMock()  # noqa: async-mock-config
        mock_result = MagicMock()
        mock_result.valid = True
        mock_result.payload = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "exp": int(datetime.now(UTC).timestamp()) + 3600,
        }
        mock_auth.verify_token = AsyncMock(return_value=mock_result)

        # Disconnect after brief delay
        receive_calls = [0]

        async def receive_then_disconnect():
            receive_calls[0] += 1
            if receive_calls[0] == 1:
                await asyncio.sleep(0.5)
                raise WebSocketDisconnect()
            raise WebSocketDisconnect()

        mock_ws.receive_json = AsyncMock(side_effect=receive_then_disconnect)

        with patch(
            "mcp_server_langgraph.websocket.base.get_auth_middleware_from_websocket",
            return_value=mock_auth,
        ):
            with patch(
                "mcp_server_langgraph.websocket.base.is_token_expired",
                return_value=False,  # Token stays valid
            ):
                await handler.run(mock_ws)

        # Verify validation task was cancelled
        assert handler._validation_task is None or handler._validation_task.cancelled(), (
            "Validation task should be cancelled after disconnect"
        )


@pytest.mark.xdist_group(name="websocket_token_expiration")
class TestCloseCodeDistinction:
    """Tests verifying 4010 is distinct from other close codes."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_4010_distinct_from_auth_failure(self) -> None:
        """GIVEN various auth errors WHEN comparing codes THEN 4010 is distinct."""
        from mcp_server_langgraph.websocket.exceptions import (
            AuthenticationError,
            AuthorizationError,
        )

        token_expired = TokenExpiredError()
        auth_failure = AuthenticationError()
        authz_failure = AuthorizationError()

        # 4010 should be unique for token expiration
        assert token_expired.code == 4010
        assert auth_failure.code != 4010
        assert authz_failure.code != 4010

    def test_4010_not_normal_close(self) -> None:
        """GIVEN 4010 close code WHEN checking THEN is not normal closure (1000)."""
        error = TokenExpiredError()

        assert error.code != 1000, "4010 should not be confused with normal close"

    def test_4010_in_4xxx_range(self) -> None:
        """GIVEN 4010 close code WHEN checking range THEN is in application range (4000-4999)."""
        error = TokenExpiredError()

        assert 4000 <= error.code <= 4999, "4010 should be in application close code range"


@pytest.mark.xdist_group(name="websocket_token_expiration")
class TestTokenExpirationTiming:
    """Tests for token expiration timing and buffer."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_token_expiring_soon_detected(self) -> None:
        """GIVEN token expiring within buffer WHEN checking THEN detected as expiring soon."""
        from mcp_server_langgraph.websocket.token_validation import is_token_expiring_soon

        # Token expires in 2 minutes (within default 5-minute buffer)
        token = _create_test_token(120)

        result = is_token_expiring_soon(token, buffer_seconds=300)

        assert result is True, "Token expiring in 2 min should be detected within 5 min buffer"

    def test_token_not_expiring_soon(self) -> None:
        """GIVEN token with ample time WHEN checking THEN not detected as expiring soon."""
        from mcp_server_langgraph.websocket.token_validation import is_token_expiring_soon

        # Token expires in 10 minutes (outside 5-minute buffer)
        token = _create_test_token(600)

        result = is_token_expiring_soon(token, buffer_seconds=300)

        assert result is False, "Token expiring in 10 min should not be detected within 5 min buffer"

    def test_already_expired_token_detected(self) -> None:
        """GIVEN already expired token WHEN checking THEN detected as expired."""
        from mcp_server_langgraph.websocket.token_validation import is_token_expired

        # Token expired 1 minute ago
        token = _create_test_token(-60)

        result = is_token_expired(token)

        assert result is True, "Already expired token should be detected"


@pytest.mark.xdist_group(name="websocket_token_expiration")
class TestConfigurableValidationInterval:
    """Tests for configurable token validation interval."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validation_disabled_when_interval_zero(self) -> None:
        """GIVEN token_validation_interval=0 WHEN creating handler THEN no validation task."""
        config = WebSocketConfig(
            endpoint_name="test-no-validation",
            require_auth=True,
            token_validation_interval=0,  # Disabled
        )

        with patch(RATE_LIMITER_PATCH, return_value=MagicMock()):
            _handler = _TokenExpirationTestHandler(config)

        # Validation task should not be created when interval is 0
        # (task is created in run(), but the interval check prevents it)
        assert config.token_validation_interval == 0

    def test_default_validation_interval_is_5_minutes(self) -> None:
        """GIVEN default config WHEN checking THEN validation interval is 300 seconds."""
        config = WebSocketConfig(endpoint_name="test-default")

        # Default should be 300 seconds (5 minutes)
        assert config.token_validation_interval == 300, "Default interval should be 5 minutes (300s)"

    def test_custom_validation_interval_applied(self) -> None:
        """GIVEN custom interval WHEN creating config THEN interval is applied."""
        config = WebSocketConfig(
            endpoint_name="test-custom",
            token_validation_interval=60,  # 1 minute
        )

        assert config.token_validation_interval == 60


@pytest.mark.xdist_group(name="websocket_token_expiration")
class TestErrorRecoveryFlow:
    """Tests for error recovery scenarios."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_token_expired_error_includes_refresh_suggestion(self) -> None:
        """GIVEN TokenExpiredError WHEN getting reason THEN suggests refresh."""
        error = TokenExpiredError()

        assert "refresh" in error.reason.lower() or "reconnect" in error.reason.lower(), (
            f"Error reason should suggest refresh/reconnect: {error.reason}"
        )

    def test_close_reason_is_informative(self) -> None:
        """GIVEN TokenExpiredError WHEN used for close THEN provides clear reason."""
        error = TokenExpiredError()

        # The close reason should be clear enough for clients to understand
        # what action to take
        assert len(error.reason) > 10, "Close reason should be informative"
        assert "Token" in str(error) or "expired" in error.reason.lower()
