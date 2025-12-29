"""
Unit tests for WebSocket Exceptions.

Tests all custom WebSocket exception classes and their attributes.
"""

import gc

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="websocket_exceptions"),
]


@pytest.mark.xdist_group(name="websocket_exceptions")
class TestWebSocketError:
    """Tests for base WebSocketError class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_error_with_defaults(self) -> None:
        """GIVEN no custom values WHEN creating error THEN uses defaults."""
        from mcp_server_langgraph.websocket.exceptions import WebSocketError

        error = WebSocketError("Test error")

        assert str(error) == "Test error"
        assert error.code == 4000
        assert error.reason == "Test error"

    def test_websocket_error_with_custom_values(self) -> None:
        """GIVEN custom values WHEN creating error THEN uses provided values."""
        from mcp_server_langgraph.websocket.exceptions import WebSocketError

        error = WebSocketError("Custom message", code=4999, reason="Custom reason")

        assert str(error) == "Custom message"
        assert error.code == 4999
        assert error.reason == "Custom reason"


@pytest.mark.xdist_group(name="websocket_exceptions")
class TestAuthenticationError:
    """Tests for AuthenticationError class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_authentication_error_with_defaults(self) -> None:
        """GIVEN no custom values WHEN creating error THEN uses defaults."""
        from mcp_server_langgraph.websocket.exceptions import AuthenticationError

        error = AuthenticationError()

        assert str(error) == "Authentication required"
        assert error.code == 4001
        assert error.reason == "Authentication required"

    def test_authentication_error_with_custom_message(self) -> None:
        """GIVEN custom message WHEN creating error THEN uses provided message."""
        from mcp_server_langgraph.websocket.exceptions import AuthenticationError

        error = AuthenticationError("Invalid token")

        assert str(error) == "Invalid token"
        assert error.code == 4001
        assert error.reason == "Authentication required"

    def test_authentication_error_with_custom_reason(self) -> None:
        """GIVEN custom reason WHEN creating error THEN uses provided reason."""
        from mcp_server_langgraph.websocket.exceptions import AuthenticationError

        error = AuthenticationError("Invalid token", reason="Token expired")

        assert str(error) == "Invalid token"
        assert error.reason == "Token expired"


@pytest.mark.xdist_group(name="websocket_exceptions")
class TestAuthorizationError:
    """Tests for AuthorizationError class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_authorization_error_with_defaults(self) -> None:
        """GIVEN no custom values WHEN creating error THEN uses defaults."""
        from mcp_server_langgraph.websocket.exceptions import AuthorizationError

        error = AuthorizationError()

        assert str(error) == "Authorization denied"
        assert error.code == 4003
        assert error.reason == "Authorization denied"
        assert error.resource is None
        assert error.relation is None

    def test_authorization_error_with_resource_and_relation(self) -> None:
        """GIVEN resource and relation WHEN creating error THEN stores them."""
        from mcp_server_langgraph.websocket.exceptions import AuthorizationError

        error = AuthorizationError(
            "Access denied",
            resource="workflow:123",
            relation="editor",
        )

        assert str(error) == "Access denied"
        assert error.resource == "workflow:123"
        assert error.relation == "editor"


@pytest.mark.xdist_group(name="websocket_exceptions")
class TestRateLimitError:
    """Tests for RateLimitError class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_rate_limit_error_with_defaults(self) -> None:
        """GIVEN no custom values WHEN creating error THEN uses defaults."""
        from mcp_server_langgraph.websocket.exceptions import RateLimitError

        error = RateLimitError()

        assert str(error) == "Rate limit exceeded"
        assert error.code == 4029
        assert error.reason == "Rate limit exceeded"
        assert error.retry_after is None

    def test_rate_limit_error_with_retry_after(self) -> None:
        """GIVEN retry_after value WHEN creating error THEN stores it."""
        from mcp_server_langgraph.websocket.exceptions import RateLimitError

        error = RateLimitError("Too many requests", retry_after=60)

        assert error.retry_after == 60


@pytest.mark.xdist_group(name="websocket_exceptions")
class TestMessageSizeError:
    """Tests for MessageSizeError class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_message_size_error_with_defaults(self) -> None:
        """GIVEN no custom values WHEN creating error THEN uses defaults."""
        from mcp_server_langgraph.websocket.exceptions import MessageSizeError

        error = MessageSizeError()

        assert str(error) == "Message too large"
        assert error.code == 4013
        assert error.reason == "Message too large"
        assert error.size is None
        assert error.max_size is None

    def test_message_size_error_with_size_info(self) -> None:
        """GIVEN size info WHEN creating error THEN stores it."""
        from mcp_server_langgraph.websocket.exceptions import MessageSizeError

        error = MessageSizeError("Payload too large", size=2048, max_size=1024)

        assert error.size == 2048
        assert error.max_size == 1024


@pytest.mark.xdist_group(name="websocket_exceptions")
class TestProtocolError:
    """Tests for ProtocolError class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_protocol_error_with_defaults(self) -> None:
        """GIVEN no custom values WHEN creating error THEN uses defaults."""
        from mcp_server_langgraph.websocket.exceptions import ProtocolError

        error = ProtocolError()

        assert str(error) == "Invalid message format"
        assert error.code == 4002
        assert error.reason == "Invalid message format"

    def test_protocol_error_with_custom_message(self) -> None:
        """GIVEN custom message WHEN creating error THEN uses provided message."""
        from mcp_server_langgraph.websocket.exceptions import ProtocolError

        error = ProtocolError("Malformed JSON")

        assert str(error) == "Malformed JSON"


@pytest.mark.xdist_group(name="websocket_exceptions")
class TestConnectionLimitError:
    """Tests for ConnectionLimitError class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_connection_limit_error_with_defaults(self) -> None:
        """GIVEN no custom values WHEN creating error THEN uses defaults."""
        from mcp_server_langgraph.websocket.exceptions import ConnectionLimitError

        error = ConnectionLimitError()

        assert str(error) == "Connection limit exceeded"
        assert error.code == 4008
        assert error.reason == "Connection limit exceeded"
        assert error.current is None
        assert error.limit is None

    def test_connection_limit_error_with_counts(self) -> None:
        """GIVEN current and limit WHEN creating error THEN stores them."""
        from mcp_server_langgraph.websocket.exceptions import ConnectionLimitError

        error = ConnectionLimitError("Too many connections", current=10, limit=5)

        assert error.current == 10
        assert error.limit == 5


@pytest.mark.xdist_group(name="websocket_exceptions")
class TestIdleTimeoutError:
    """Tests for IdleTimeoutError class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_idle_timeout_error_with_defaults(self) -> None:
        """GIVEN no custom values WHEN creating error THEN uses defaults."""
        from mcp_server_langgraph.websocket.exceptions import IdleTimeoutError

        error = IdleTimeoutError()

        assert str(error) == "Connection timed out"
        assert error.code == 4008
        assert error.reason == "Connection timed out due to inactivity"
        assert error.idle_seconds is None

    def test_idle_timeout_error_with_idle_seconds(self) -> None:
        """GIVEN idle_seconds value WHEN creating error THEN stores it."""
        from mcp_server_langgraph.websocket.exceptions import IdleTimeoutError

        error = IdleTimeoutError("Timed out", idle_seconds=300)

        assert error.idle_seconds == 300


@pytest.mark.xdist_group(name="websocket_exceptions")
class TestHeartbeatTimeoutError:
    """Tests for HeartbeatTimeoutError class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_heartbeat_timeout_error_with_defaults(self) -> None:
        """GIVEN no custom values WHEN creating error THEN uses defaults."""
        from mcp_server_langgraph.websocket.exceptions import HeartbeatTimeoutError

        error = HeartbeatTimeoutError()

        assert str(error) == "Heartbeat timeout"
        assert error.code == 4008
        assert error.reason == "Heartbeat timeout"
        assert error.missed_count is None

    def test_heartbeat_timeout_error_with_missed_count(self) -> None:
        """GIVEN missed_count value WHEN creating error THEN stores it."""
        from mcp_server_langgraph.websocket.exceptions import HeartbeatTimeoutError

        error = HeartbeatTimeoutError("No heartbeat", missed_count=3)

        assert error.missed_count == 3


@pytest.mark.xdist_group(name="websocket_exceptions")
class TestSubscriptionError:
    """Tests for SubscriptionError class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_subscription_error_with_defaults(self) -> None:
        """GIVEN no custom values WHEN creating error THEN uses defaults."""
        from mcp_server_langgraph.websocket.exceptions import SubscriptionError

        error = SubscriptionError()

        assert str(error) == "Subscription failed"
        assert error.code == 4004
        assert error.reason == "Subscription failed"
        assert error.resource_id is None

    def test_subscription_error_with_resource_id(self) -> None:
        """GIVEN resource_id value WHEN creating error THEN stores it."""
        from mcp_server_langgraph.websocket.exceptions import SubscriptionError

        error = SubscriptionError("Cannot subscribe", resource_id="workflow:123")

        assert error.resource_id == "workflow:123"


@pytest.mark.xdist_group(name="websocket_exceptions")
class TestTokenExpiredError:
    """Tests for TokenExpiredError class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_token_expired_error_has_code_4010(self) -> None:
        """GIVEN TokenExpiredError WHEN instantiated THEN code is 4010."""
        from mcp_server_langgraph.websocket.exceptions import TokenExpiredError

        error = TokenExpiredError()

        assert error.code == 4010

    def test_token_expired_error_with_defaults(self) -> None:
        """GIVEN no custom values WHEN creating error THEN uses defaults."""
        from mcp_server_langgraph.websocket.exceptions import TokenExpiredError

        error = TokenExpiredError()

        assert str(error) == "Token expired"
        assert error.code == 4010
        assert error.reason == "Token expired. Please refresh and reconnect."

    def test_token_expired_error_inherits_from_authentication_error(self) -> None:
        """GIVEN TokenExpiredError WHEN checking inheritance THEN is AuthenticationError."""
        from mcp_server_langgraph.websocket.exceptions import (
            AuthenticationError,
            TokenExpiredError,
        )

        error = TokenExpiredError()

        assert isinstance(error, AuthenticationError)

    def test_token_expired_error_with_custom_message(self) -> None:
        """GIVEN custom message WHEN creating error THEN uses provided message."""
        from mcp_server_langgraph.websocket.exceptions import TokenExpiredError

        error = TokenExpiredError("Access token has expired")

        assert str(error) == "Access token has expired"
        assert error.code == 4010

    def test_token_expired_error_with_custom_reason(self) -> None:
        """GIVEN custom reason WHEN creating error THEN uses provided reason."""
        from mcp_server_langgraph.websocket.exceptions import TokenExpiredError

        error = TokenExpiredError(reason="Session expired after 30 minutes")

        assert error.reason == "Session expired after 30 minutes"

    def test_token_expired_error_can_be_caught_as_websocket_error(self) -> None:
        """GIVEN TokenExpiredError WHEN raised THEN can be caught as WebSocketError."""
        from mcp_server_langgraph.websocket.exceptions import (
            TokenExpiredError,
            WebSocketError,
        )

        with pytest.raises(WebSocketError) as exc_info:
            raise TokenExpiredError()

        assert exc_info.value.code == 4010


@pytest.mark.xdist_group(name="websocket_exceptions")
class TestExceptionHierarchy:
    """Tests for exception class hierarchy."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_errors_inherit_from_websocket_error(self) -> None:
        """GIVEN all exception classes WHEN checking inheritance THEN all inherit from WebSocketError."""
        from mcp_server_langgraph.websocket.exceptions import (
            AuthenticationError,
            AuthorizationError,
            ConnectionLimitError,
            HeartbeatTimeoutError,
            IdleTimeoutError,
            MessageSizeError,
            ProtocolError,
            RateLimitError,
            SubscriptionError,
            TokenExpiredError,
            WebSocketError,
        )

        exception_classes = [
            AuthenticationError,
            AuthorizationError,
            RateLimitError,
            MessageSizeError,
            ProtocolError,
            ConnectionLimitError,
            IdleTimeoutError,
            HeartbeatTimeoutError,
            SubscriptionError,
            TokenExpiredError,
        ]

        for cls in exception_classes:
            assert issubclass(cls, WebSocketError), f"{cls.__name__} should inherit from WebSocketError"
            assert issubclass(cls, Exception), f"{cls.__name__} should inherit from Exception"

    def test_websocket_error_inherits_from_exception(self) -> None:
        """GIVEN WebSocketError WHEN checking inheritance THEN inherits from Exception."""
        from mcp_server_langgraph.websocket.exceptions import WebSocketError

        assert issubclass(WebSocketError, Exception)

    def test_errors_can_be_raised_and_caught(self) -> None:
        """GIVEN exception instances WHEN raised THEN can be caught by base class."""
        from mcp_server_langgraph.websocket.exceptions import (
            AuthenticationError,
            WebSocketError,
        )

        with pytest.raises(WebSocketError) as exc_info:
            raise AuthenticationError("Test")

        assert exc_info.value.code == 4001
