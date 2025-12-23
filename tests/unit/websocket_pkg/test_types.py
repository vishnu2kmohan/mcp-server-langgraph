"""
Unit tests for WebSocket Types.

Tests the type definitions, dataclasses, and protocols for WebSocket infrastructure.
"""

import gc
from datetime import UTC, datetime

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="websocket_types"),
]


@pytest.mark.xdist_group(name="websocket_types")
class TestConnectionState:
    """Tests for ConnectionState enum."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_connection_state_values(self) -> None:
        """GIVEN ConnectionState enum WHEN accessing values THEN returns expected strings."""
        from mcp_server_langgraph.websocket.types import ConnectionState

        assert ConnectionState.CONNECTING.value == "connecting"
        assert ConnectionState.CONNECTED.value == "connected"
        assert ConnectionState.AUTHENTICATING.value == "authenticating"
        assert ConnectionState.AUTHORIZED.value == "authorized"
        assert ConnectionState.DISCONNECTING.value == "disconnecting"
        assert ConnectionState.DISCONNECTED.value == "disconnected"
        assert ConnectionState.ERROR.value == "error"

    def test_connection_state_is_string_enum(self) -> None:
        """GIVEN ConnectionState value WHEN accessing value THEN returns string."""
        from mcp_server_langgraph.websocket.types import ConnectionState

        # StrEnum .value returns string
        connected_value = ConnectionState.CONNECTED.value
        assert connected_value == "connected"
        assert isinstance(connected_value, str)


@pytest.mark.xdist_group(name="websocket_types")
class TestMessageType:
    """Tests for MessageType enum."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_message_type_client_messages(self) -> None:
        """GIVEN MessageType enum WHEN accessing client messages THEN returns expected values."""
        from mcp_server_langgraph.websocket.types import MessageType

        assert MessageType.PING.value == "ping"
        assert MessageType.SUBSCRIBE.value == "subscribe"
        assert MessageType.UNSUBSCRIBE.value == "unsubscribe"

    def test_message_type_server_messages(self) -> None:
        """GIVEN MessageType enum WHEN accessing server messages THEN returns expected values."""
        from mcp_server_langgraph.websocket.types import MessageType

        assert MessageType.PONG.value == "pong"
        assert MessageType.HEARTBEAT.value == "heartbeat"
        assert MessageType.CONNECTED.value == "connected"
        assert MessageType.ERROR.value == "error"
        assert MessageType.SUBSCRIBED.value == "subscribed"
        assert MessageType.UNSUBSCRIBED.value == "unsubscribed"


@pytest.mark.xdist_group(name="websocket_types")
class TestMessageEnvelope:
    """Tests for MessageEnvelope dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_message_envelope_minimal(self) -> None:
        """GIVEN only type WHEN creating envelope THEN sets defaults for optional fields."""
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        envelope = MessageEnvelope(type="test")

        assert envelope.type == "test"
        assert envelope.payload is None
        assert envelope.id is None
        assert envelope.timestamp is None

    def test_message_envelope_full(self) -> None:
        """GIVEN all fields WHEN creating envelope THEN stores all values."""
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        now = datetime.now(UTC)
        envelope = MessageEnvelope(
            type="test",
            payload={"key": "value"},
            id="msg-123",
            timestamp=now,
        )

        assert envelope.type == "test"
        assert envelope.payload == {"key": "value"}
        assert envelope.id == "msg-123"
        assert envelope.timestamp == now

    def test_to_dict_minimal(self) -> None:
        """GIVEN minimal envelope WHEN to_dict called THEN returns only type."""
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        envelope = MessageEnvelope(type="test")
        result = envelope.to_dict()

        assert result == {"type": "test"}
        assert "payload" not in result
        assert "id" not in result
        assert "timestamp" not in result

    def test_to_dict_with_payload(self) -> None:
        """GIVEN envelope with payload WHEN to_dict called THEN includes payload."""
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        envelope = MessageEnvelope(type="test", payload={"data": 123})
        result = envelope.to_dict()

        assert result == {"type": "test", "payload": {"data": 123}}

    def test_to_dict_with_id(self) -> None:
        """GIVEN envelope with id WHEN to_dict called THEN includes id."""
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        envelope = MessageEnvelope(type="test", id="msg-456")
        result = envelope.to_dict()

        assert result == {"type": "test", "id": "msg-456"}

    def test_to_dict_with_timestamp(self) -> None:
        """GIVEN envelope with timestamp WHEN to_dict called THEN includes ISO timestamp."""
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        now = datetime(2025, 1, 15, 12, 30, 45, tzinfo=UTC)
        envelope = MessageEnvelope(type="test", timestamp=now)
        result = envelope.to_dict()

        assert result["type"] == "test"
        assert result["timestamp"] == "2025-01-15T12:30:45+00:00"

    def test_to_dict_full(self) -> None:
        """GIVEN full envelope WHEN to_dict called THEN includes all fields."""
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        now = datetime(2025, 1, 15, 12, 30, 45, tzinfo=UTC)
        envelope = MessageEnvelope(
            type="test",
            payload={"key": "value"},
            id="msg-789",
            timestamp=now,
        )
        result = envelope.to_dict()

        assert result == {
            "type": "test",
            "payload": {"key": "value"},
            "id": "msg-789",
            "timestamp": "2025-01-15T12:30:45+00:00",
        }

    def test_from_dict_minimal(self) -> None:
        """GIVEN minimal dict WHEN from_dict called THEN creates envelope."""
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        data = {"type": "test"}
        envelope = MessageEnvelope.from_dict(data)

        assert envelope.type == "test"
        assert envelope.payload is None
        assert envelope.id is None
        assert envelope.timestamp is None

    def test_from_dict_full(self) -> None:
        """GIVEN full dict WHEN from_dict called THEN creates envelope with all fields."""
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        data = {
            "type": "test",
            "payload": {"key": "value"},
            "id": "msg-123",
            "timestamp": "2025-01-15T12:30:45+00:00",
        }
        envelope = MessageEnvelope.from_dict(data)

        assert envelope.type == "test"
        assert envelope.payload == {"key": "value"}
        assert envelope.id == "msg-123"
        assert envelope.timestamp is not None
        assert envelope.timestamp.year == 2025
        assert envelope.timestamp.month == 1
        assert envelope.timestamp.day == 15

    def test_from_dict_empty_type(self) -> None:
        """GIVEN empty dict WHEN from_dict called THEN uses unknown as type."""
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        envelope = MessageEnvelope.from_dict({})

        assert envelope.type == "unknown"

    def test_from_dict_empty_timestamp(self) -> None:
        """GIVEN empty timestamp WHEN from_dict called THEN timestamp is None."""
        from mcp_server_langgraph.websocket.types import MessageEnvelope

        data = {"type": "test", "timestamp": ""}
        envelope = MessageEnvelope.from_dict(data)

        assert envelope.timestamp is None


@pytest.mark.xdist_group(name="websocket_types")
class TestAuthUser:
    """Tests for AuthUser dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_auth_user_minimal(self) -> None:
        """GIVEN minimal values WHEN creating auth user THEN sets defaults."""
        from mcp_server_langgraph.websocket.types import AuthUser

        user = AuthUser(id="user-123", username="testuser")

        assert user.id == "user-123"
        assert user.username == "testuser"
        assert user.email is None
        assert user.roles == []
        assert user.realm_access == {}
        assert user.resource_access == {}
        assert user.raw_claims == {}

    def test_auth_user_full(self) -> None:
        """GIVEN all values WHEN creating auth user THEN stores all."""
        from mcp_server_langgraph.websocket.types import AuthUser

        user = AuthUser(
            id="user-123",
            username="testuser",
            email="test@example.com",
            roles=["admin", "user"],
            realm_access={"roles": ["admin"]},
            resource_access={"api": {"roles": ["read"]}},
            raw_claims={"custom": "claim"},
        )

        assert user.email == "test@example.com"
        assert user.roles == ["admin", "user"]
        assert user.realm_access == {"roles": ["admin"]}
        assert user.resource_access == {"api": {"roles": ["read"]}}
        assert user.raw_claims == {"custom": "claim"}

    def test_from_jwt_payload_with_sub(self) -> None:
        """GIVEN JWT with sub claim WHEN from_jwt_payload THEN uses sub as id."""
        from mcp_server_langgraph.websocket.types import AuthUser

        payload = {
            "sub": "user-123",
            "preferred_username": "testuser",
            "email": "test@example.com",
            "realm_access": {"roles": ["admin", "user"]},
            "resource_access": {"api": {"roles": ["read"]}},
        }
        user = AuthUser.from_jwt_payload(payload)

        assert user.id == "user-123"
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.roles == ["admin", "user"]
        assert user.raw_claims == payload

    def test_from_jwt_payload_with_user_id_fallback(self) -> None:
        """GIVEN JWT with user_id claim WHEN from_jwt_payload THEN uses user_id as id."""
        from mcp_server_langgraph.websocket.types import AuthUser

        payload = {"user_id": "user-456", "name": "Test User"}
        user = AuthUser.from_jwt_payload(payload)

        assert user.id == "user-456"
        assert user.username == "Test User"

    def test_from_jwt_payload_with_preferred_username_fallback(self) -> None:
        """GIVEN JWT with only preferred_username WHEN from_jwt_payload THEN uses it."""
        from mcp_server_langgraph.websocket.types import AuthUser

        payload = {"preferred_username": "testuser"}
        user = AuthUser.from_jwt_payload(payload)

        assert user.id == "testuser"
        assert user.username == "testuser"

    def test_from_jwt_payload_empty(self) -> None:
        """GIVEN empty JWT payload WHEN from_jwt_payload THEN uses unknown defaults."""
        from mcp_server_langgraph.websocket.types import AuthUser

        user = AuthUser.from_jwt_payload({})

        assert user.id == "unknown"
        assert user.username == "unknown"
        assert user.email is None
        assert user.roles == []

    def test_has_role_true(self) -> None:
        """GIVEN user with role WHEN has_role called THEN returns True."""
        from mcp_server_langgraph.websocket.types import AuthUser

        user = AuthUser(id="u1", username="u1", roles=["admin", "user"])

        assert user.has_role("admin") is True
        assert user.has_role("user") is True

    def test_has_role_false(self) -> None:
        """GIVEN user without role WHEN has_role called THEN returns False."""
        from mcp_server_langgraph.websocket.types import AuthUser

        user = AuthUser(id="u1", username="u1", roles=["user"])

        assert user.has_role("admin") is False

    def test_has_any_role_true(self) -> None:
        """GIVEN user with one matching role WHEN has_any_role called THEN returns True."""
        from mcp_server_langgraph.websocket.types import AuthUser

        user = AuthUser(id="u1", username="u1", roles=["user"])

        assert user.has_any_role(["admin", "user"]) is True

    def test_has_any_role_false(self) -> None:
        """GIVEN user with no matching roles WHEN has_any_role called THEN returns False."""
        from mcp_server_langgraph.websocket.types import AuthUser

        user = AuthUser(id="u1", username="u1", roles=["viewer"])

        assert user.has_any_role(["admin", "editor"]) is False

    def test_has_any_role_empty_list(self) -> None:
        """GIVEN empty role list WHEN has_any_role called THEN returns False."""
        from mcp_server_langgraph.websocket.types import AuthUser

        user = AuthUser(id="u1", username="u1", roles=["admin"])

        assert user.has_any_role([]) is False


@pytest.mark.xdist_group(name="websocket_types")
class TestWebSocketConfig:
    """Tests for WebSocketConfig dataclass."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_config_defaults(self) -> None:
        """GIVEN no custom values WHEN creating config THEN uses defaults."""
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig()

        assert config.require_auth is True
        assert config.required_roles == []
        assert config.authz_resource_type is None
        assert config.authz_required_relation == "viewer"
        assert config.authz_fail_closed is True
        assert config.rate_limit_per_minute == 600
        assert config.rate_limit_burst == 50
        assert config.heartbeat_interval == 30
        assert config.heartbeat_timeout == 90
        assert config.idle_timeout == 1800
        assert config.max_message_size == 1_000_000
        assert config.max_connections_per_user == 5
        assert config.message_timeout == 30
        assert config.endpoint_name == "unknown"
        assert config.enable_tracing is True

    def test_websocket_config_custom(self) -> None:
        """GIVEN custom values WHEN creating config THEN uses provided values."""
        from mcp_server_langgraph.websocket.types import WebSocketConfig

        config = WebSocketConfig(
            require_auth=False,
            required_roles=["admin"],
            rate_limit_per_minute=100,
            endpoint_name="test-endpoint",
        )

        assert config.require_auth is False
        assert config.required_roles == ["admin"]
        assert config.rate_limit_per_minute == 100
        assert config.endpoint_name == "test-endpoint"


@pytest.mark.xdist_group(name="websocket_types")
class TestProtocols:
    """Tests for WebSocket protocol definitions."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_websocket_handler_is_runtime_checkable(self) -> None:
        """GIVEN WebSocketHandler protocol WHEN checking if runtime_checkable THEN is True."""
        from mcp_server_langgraph.websocket.types import WebSocketHandler

        assert hasattr(WebSocketHandler, "__protocol_attrs__") or hasattr(
            WebSocketHandler, "_is_protocol"
        )

    def test_websocket_lifecycle_is_runtime_checkable(self) -> None:
        """GIVEN WebSocketLifecycle protocol WHEN checking if runtime_checkable THEN is True."""
        from mcp_server_langgraph.websocket.types import WebSocketLifecycle

        assert hasattr(WebSocketLifecycle, "__protocol_attrs__") or hasattr(
            WebSocketLifecycle, "_is_protocol"
        )

    def test_class_implementing_handler_passes_isinstance(self) -> None:
        """GIVEN class implementing handle_message WHEN isinstance checked THEN passes."""
        from mcp_server_langgraph.websocket.types import MessageEnvelope, WebSocketHandler

        class MyHandler:
            async def handle_message(self, message: MessageEnvelope) -> MessageEnvelope | None:
                return None

        handler = MyHandler()
        assert isinstance(handler, WebSocketHandler)

    def test_class_implementing_lifecycle_passes_isinstance(self) -> None:
        """GIVEN class implementing lifecycle methods WHEN isinstance checked THEN passes."""
        from mcp_server_langgraph.websocket.types import AuthUser, WebSocketLifecycle

        class MyLifecycle:
            async def on_connect(self, user: AuthUser) -> None:
                pass

            async def on_disconnect(self) -> None:
                pass

            async def on_error(self, error: Exception) -> None:
                pass

        lifecycle = MyLifecycle()
        assert isinstance(lifecycle, WebSocketLifecycle)
