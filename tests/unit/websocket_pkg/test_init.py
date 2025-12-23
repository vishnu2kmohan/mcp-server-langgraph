"""
Unit tests for WebSocket module __init__.py.

Tests that all public exports are correctly accessible through lazy loading.
"""

from __future__ import annotations

import gc

import pytest

pytestmark = [
    pytest.mark.unit,
    pytest.mark.websocket,
    pytest.mark.xdist_group(name="websocket_init"),
]


@pytest.mark.xdist_group(name="websocket_init")
class TestWebSocketModuleExports:
    """Tests for lazy import functionality in websocket module."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    # =========================================================================
    # Types - Eagerly imported
    # =========================================================================

    def test_auth_user_export(self) -> None:
        """GIVEN websocket module WHEN importing AuthUser THEN succeeds."""
        from mcp_server_langgraph.websocket import AuthUser

        assert AuthUser is not None

    def test_connection_state_export(self) -> None:
        """GIVEN websocket module WHEN importing ConnectionState THEN succeeds."""
        from mcp_server_langgraph.websocket import ConnectionState

        assert ConnectionState is not None

    def test_message_envelope_export(self) -> None:
        """GIVEN websocket module WHEN importing MessageEnvelope THEN succeeds."""
        from mcp_server_langgraph.websocket import MessageEnvelope

        assert MessageEnvelope is not None

    def test_message_type_export(self) -> None:
        """GIVEN websocket module WHEN importing MessageType THEN succeeds."""
        from mcp_server_langgraph.websocket import MessageType

        assert MessageType is not None

    def test_websocket_config_export(self) -> None:
        """GIVEN websocket module WHEN importing WebSocketConfig THEN succeeds."""
        from mcp_server_langgraph.websocket import WebSocketConfig

        assert WebSocketConfig is not None

    def test_websocket_handler_export(self) -> None:
        """GIVEN websocket module WHEN importing WebSocketHandler THEN succeeds."""
        from mcp_server_langgraph.websocket import WebSocketHandler

        assert WebSocketHandler is not None

    def test_websocket_lifecycle_export(self) -> None:
        """GIVEN websocket module WHEN importing WebSocketLifecycle THEN succeeds."""
        from mcp_server_langgraph.websocket import WebSocketLifecycle

        assert WebSocketLifecycle is not None

    # =========================================================================
    # Exceptions - Eagerly imported
    # =========================================================================

    def test_websocket_error_export(self) -> None:
        """GIVEN websocket module WHEN importing WebSocketError THEN succeeds."""
        from mcp_server_langgraph.websocket import WebSocketError

        assert WebSocketError is not None

    def test_authentication_error_export(self) -> None:
        """GIVEN websocket module WHEN importing AuthenticationError THEN succeeds."""
        from mcp_server_langgraph.websocket import AuthenticationError

        assert AuthenticationError is not None

    def test_authorization_error_export(self) -> None:
        """GIVEN websocket module WHEN importing AuthorizationError THEN succeeds."""
        from mcp_server_langgraph.websocket import AuthorizationError

        assert AuthorizationError is not None

    def test_rate_limit_error_export(self) -> None:
        """GIVEN websocket module WHEN importing RateLimitError THEN succeeds."""
        from mcp_server_langgraph.websocket import RateLimitError

        assert RateLimitError is not None

    def test_message_size_error_export(self) -> None:
        """GIVEN websocket module WHEN importing MessageSizeError THEN succeeds."""
        from mcp_server_langgraph.websocket import MessageSizeError

        assert MessageSizeError is not None

    def test_protocol_error_export(self) -> None:
        """GIVEN websocket module WHEN importing ProtocolError THEN succeeds."""
        from mcp_server_langgraph.websocket import ProtocolError

        assert ProtocolError is not None

    def test_connection_limit_error_export(self) -> None:
        """GIVEN websocket module WHEN importing ConnectionLimitError THEN succeeds."""
        from mcp_server_langgraph.websocket import ConnectionLimitError

        assert ConnectionLimitError is not None

    def test_idle_timeout_error_export(self) -> None:
        """GIVEN websocket module WHEN importing IdleTimeoutError THEN succeeds."""
        from mcp_server_langgraph.websocket import IdleTimeoutError

        assert IdleTimeoutError is not None

    def test_heartbeat_timeout_error_export(self) -> None:
        """GIVEN websocket module WHEN importing HeartbeatTimeoutError THEN succeeds."""
        from mcp_server_langgraph.websocket import HeartbeatTimeoutError

        assert HeartbeatTimeoutError is not None

    def test_subscription_error_export(self) -> None:
        """GIVEN websocket module WHEN importing SubscriptionError THEN succeeds."""
        from mcp_server_langgraph.websocket import SubscriptionError

        assert SubscriptionError is not None

    # =========================================================================
    # Lazy Imports - Via __getattr__
    # =========================================================================

    def test_websocket_base_lazy_import(self) -> None:
        """GIVEN websocket module WHEN importing WebSocketBase THEN lazy loads."""
        from mcp_server_langgraph.websocket import WebSocketBase

        assert WebSocketBase is not None

    def test_websocket_authorization_middleware_lazy_import(self) -> None:
        """GIVEN websocket module WHEN importing WebSocketAuthorizationMiddleware THEN lazy loads."""
        from mcp_server_langgraph.websocket import WebSocketAuthorizationMiddleware

        assert WebSocketAuthorizationMiddleware is not None

    def test_heartbeat_manager_lazy_import(self) -> None:
        """GIVEN websocket module WHEN importing HeartbeatManager THEN lazy loads."""
        from mcp_server_langgraph.websocket import HeartbeatManager

        assert HeartbeatManager is not None

    def test_websocket_metrics_lazy_import(self) -> None:
        """GIVEN websocket module WHEN importing WebSocketMetrics THEN lazy loads."""
        from mcp_server_langgraph.websocket import WebSocketMetrics

        assert WebSocketMetrics is not None

    def test_websocket_rate_limiter_lazy_import(self) -> None:
        """GIVEN websocket module WHEN importing WebSocketRateLimiter THEN lazy loads."""
        from mcp_server_langgraph.websocket import WebSocketRateLimiter

        assert WebSocketRateLimiter is not None

    def test_message_rate_limiter_lazy_import(self) -> None:
        """GIVEN websocket module WHEN importing MessageRateLimiter THEN lazy loads."""
        from mcp_server_langgraph.websocket import MessageRateLimiter

        assert MessageRateLimiter is not None

    def test_user_rate_limiter_lazy_import(self) -> None:
        """GIVEN websocket module WHEN importing UserRateLimiter THEN lazy loads."""
        from mcp_server_langgraph.websocket import UserRateLimiter

        assert UserRateLimiter is not None

    def test_connection_rate_limiter_lazy_import(self) -> None:
        """GIVEN websocket module WHEN importing ConnectionRateLimiter THEN lazy loads."""
        from mcp_server_langgraph.websocket import ConnectionRateLimiter

        assert ConnectionRateLimiter is not None

    def test_redis_user_rate_limiter_lazy_import(self) -> None:
        """GIVEN websocket module WHEN importing RedisUserRateLimiter THEN lazy loads."""
        from mcp_server_langgraph.websocket import RedisUserRateLimiter

        assert RedisUserRateLimiter is not None

    def test_redis_websocket_rate_limiter_lazy_import(self) -> None:
        """GIVEN websocket module WHEN importing RedisWebSocketRateLimiter THEN lazy loads."""
        from mcp_server_langgraph.websocket import RedisWebSocketRateLimiter

        assert RedisWebSocketRateLimiter is not None

    def test_create_redis_rate_limiter_lazy_import(self) -> None:
        """GIVEN websocket module WHEN importing create_redis_rate_limiter THEN lazy loads."""
        from mcp_server_langgraph.websocket import create_redis_rate_limiter

        assert create_redis_rate_limiter is not None
        assert callable(create_redis_rate_limiter)

    def test_get_websocket_rate_limiter_lazy_import(self) -> None:
        """GIVEN websocket module WHEN importing get_websocket_rate_limiter THEN lazy loads."""
        from mcp_server_langgraph.websocket import get_websocket_rate_limiter

        assert get_websocket_rate_limiter is not None
        assert callable(get_websocket_rate_limiter)

    # Resilience utilities
    def test_with_circuit_breaker_lazy_import(self) -> None:
        """GIVEN websocket module WHEN importing with_circuit_breaker THEN lazy loads."""
        from mcp_server_langgraph.websocket import with_circuit_breaker

        assert with_circuit_breaker is not None

    def test_get_circuit_breaker_state_lazy_import(self) -> None:
        """GIVEN websocket module WHEN importing get_circuit_breaker_state THEN lazy loads."""
        from mcp_server_langgraph.websocket import get_circuit_breaker_state

        assert get_circuit_breaker_state is not None

    def test_is_circuit_open_lazy_import(self) -> None:
        """GIVEN websocket module WHEN importing is_circuit_open THEN lazy loads."""
        from mcp_server_langgraph.websocket import is_circuit_open

        assert is_circuit_open is not None

    def test_websocket_services_lazy_import(self) -> None:
        """GIVEN websocket module WHEN importing WebSocketServices THEN lazy loads."""
        from mcp_server_langgraph.websocket import WebSocketServices

        assert WebSocketServices is not None

    # Middleware utilities
    def test_extract_websocket_token_lazy_import(self) -> None:
        """GIVEN websocket module WHEN importing extract_websocket_token THEN lazy loads."""
        from mcp_server_langgraph.websocket import extract_websocket_token

        assert extract_websocket_token is not None
        assert callable(extract_websocket_token)

    def test_validate_websocket_auth_lazy_import(self) -> None:
        """GIVEN websocket module WHEN importing validate_websocket_auth THEN lazy loads."""
        from mcp_server_langgraph.websocket import validate_websocket_auth

        assert validate_websocket_auth is not None
        assert callable(validate_websocket_auth)

    def test_extract_user_from_jwt_payload_lazy_import(self) -> None:
        """GIVEN websocket module WHEN importing extract_user_from_jwt_payload THEN lazy loads."""
        from mcp_server_langgraph.websocket import extract_user_from_jwt_payload

        assert extract_user_from_jwt_payload is not None
        assert callable(extract_user_from_jwt_payload)

    def test_validate_websocket_token_lazy_import(self) -> None:
        """GIVEN websocket module WHEN importing validate_websocket_token THEN lazy loads."""
        from mcp_server_langgraph.websocket import validate_websocket_token

        assert validate_websocket_token is not None
        assert callable(validate_websocket_token)


@pytest.mark.xdist_group(name="websocket_init")
class TestWebSocketModuleAttributeError:
    """Tests for __getattr__ error handling."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_unknown_attribute_raises_attribute_error(self) -> None:
        """GIVEN websocket module WHEN importing unknown attribute THEN raises AttributeError."""
        import mcp_server_langgraph.websocket as ws_module

        with pytest.raises(AttributeError) as exc_info:
            _ = ws_module.NonExistentClass

        assert "NonExistentClass" in str(exc_info.value)


@pytest.mark.xdist_group(name="websocket_init")
class TestWebSocketModuleAll:
    """Tests for __all__ export list."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_all_contains_expected_exports(self) -> None:
        """GIVEN websocket module WHEN checking __all__ THEN contains all exports."""
        import mcp_server_langgraph.websocket as ws_module

        expected_exports = [
            "WebSocketBase",
            "WebSocketAuthorizationMiddleware",
            "HeartbeatManager",
            "WebSocketMetrics",
            "WebSocketRateLimiter",
            "MessageRateLimiter",
            "UserRateLimiter",
            "ConnectionRateLimiter",
            "RedisUserRateLimiter",
            "RedisWebSocketRateLimiter",
            "create_redis_rate_limiter",
            "get_websocket_rate_limiter",
            "AuthUser",
            "ConnectionState",
            "MessageEnvelope",
            "MessageType",
            "WebSocketConfig",
            "WebSocketHandler",
            "WebSocketLifecycle",
            "WebSocketError",
            "AuthenticationError",
            "AuthorizationError",
            "RateLimitError",
            "MessageSizeError",
            "ProtocolError",
            "ConnectionLimitError",
            "IdleTimeoutError",
            "HeartbeatTimeoutError",
            "SubscriptionError",
            "with_circuit_breaker",
            "get_circuit_breaker_state",
            "is_circuit_open",
            "WebSocketServices",
            "extract_websocket_token",
            "validate_websocket_auth",
            "extract_user_from_jwt_payload",
            "validate_websocket_token",
        ]

        for export in expected_exports:
            assert export in ws_module.__all__, f"{export} not in __all__"

    def test_all_exports_are_accessible(self) -> None:
        """GIVEN websocket module WHEN accessing __all__ exports THEN all work."""
        import mcp_server_langgraph.websocket as ws_module

        for name in ws_module.__all__:
            obj = getattr(ws_module, name)
            assert obj is not None, f"{name} is None"
