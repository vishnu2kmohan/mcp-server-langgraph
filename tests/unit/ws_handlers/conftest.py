"""
WebSocket Test Fixtures.

Provides common fixtures for WebSocket unit tests.
"""

from __future__ import annotations

import gc
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import WebSocket

from mcp_server_langgraph.websocket import AuthUser, MessageEnvelope, WebSocketConfig


@pytest.fixture
def sample_user() -> AuthUser:
    """Create a sample authenticated user for tests."""
    return AuthUser(
        id="test-user-123",
        username="testuser",
        email="test@example.com",
        roles=["user", "developer"],
        realm_access={"roles": ["user", "developer"]},
        resource_access={},
        raw_claims={
            "sub": "test-user-123",
            "preferred_username": "testuser",
            "email": "test@example.com",
        },
    )


@pytest.fixture
def admin_user() -> AuthUser:
    """Create an admin user for tests."""
    return AuthUser(
        id="admin",
        username="admin",
        email="admin@example.com",
        roles=["admin", "user"],
        realm_access={"roles": ["admin", "user"]},
        resource_access={},
        raw_claims={
            "sub": "admin",
            "preferred_username": "admin",
            "email": "admin@example.com",
        },
    )


@pytest.fixture
def alice_user() -> AuthUser:
    """Create alice user (developer persona) for tests."""
    return AuthUser(
        id="alice",
        username="alice",
        email="alice@example.com",
        roles=["developer", "user"],
        realm_access={"roles": ["developer", "user"]},
        resource_access={},
        raw_claims={
            "sub": "alice",
            "preferred_username": "alice",
            "email": "alice@example.com",
        },
    )


@pytest.fixture
def bob_user() -> AuthUser:
    """Create bob user (basic persona) for tests."""
    return AuthUser(
        id="bob",
        username="bob",
        email="bob@example.com",
        roles=["user"],
        realm_access={"roles": ["user"]},
        resource_access={},
        raw_claims={
            "sub": "bob",
            "preferred_username": "bob",
            "email": "bob@example.com",
        },
    )


@pytest.fixture
def sample_config() -> WebSocketConfig:
    """Create a sample WebSocket configuration."""
    return WebSocketConfig(
        require_auth=True,
        required_roles=[],
        authz_resource_type="dashboard",
        authz_resource_id="test",
        authz_required_relation="viewer",
        authz_fail_closed=True,
        rate_limit_per_minute=600,
        heartbeat_interval=30,
        idle_timeout=1800,
        max_message_size=1_000_000,
        endpoint_name="test-endpoint",
    )


@pytest.fixture
def mock_websocket() -> MagicMock:
    """Create a mock WebSocket for testing."""
    # Don't use spec to allow __bool__ to work correctly
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    ws.send_json = AsyncMock()
    ws.send_text = AsyncMock()
    ws.receive_json = AsyncMock()
    ws.receive_text = AsyncMock()
    ws.query_params = {}
    ws.headers = {}
    ws.client_state = MagicMock()
    return ws


@pytest.fixture
def sample_message() -> MessageEnvelope:
    """Create a sample message envelope."""
    return MessageEnvelope(
        type="test",
        payload={"key": "value"},
        id="msg-123",
    )


@pytest.fixture
def ping_message() -> MessageEnvelope:
    """Create a ping message."""
    return MessageEnvelope(type="ping")


@pytest.fixture
def subscribe_message() -> MessageEnvelope:
    """Create a subscribe message."""
    return MessageEnvelope(
        type="subscribe",
        payload={"resource_id": "test-resource"},
    )


class TestWebSocketFixtures:
    """Test that fixtures are properly configured."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_sample_user_has_required_fields(self, sample_user: AuthUser) -> None:
        """Sample user should have all required fields."""
        assert sample_user.id == "test-user-123"
        assert sample_user.username == "testuser"
        assert "user" in sample_user.roles

    def test_admin_user_has_admin_role(self, admin_user: AuthUser) -> None:
        """Admin user should have admin role."""
        assert admin_user.has_role("admin")
        assert admin_user.has_any_role(["admin", "superuser"])

    def test_sample_config_has_defaults(self, sample_config: WebSocketConfig) -> None:
        """Sample config should have sensible defaults."""
        assert sample_config.require_auth is True
        assert sample_config.heartbeat_interval == 30
        assert sample_config.rate_limit_per_minute == 600
