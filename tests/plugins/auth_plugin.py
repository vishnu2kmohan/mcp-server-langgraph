"""
Authentication Fixtures Plugin.

Provides fixtures for authentication and user management in tests.
Extracted from conftest.py for better organization.
"""

from datetime import UTC, datetime, timedelta

import pytest

from tests.constants import TEST_JWT_SECRET


@pytest.fixture
def mock_current_user():
    """
    Shared mock current user fixture for API endpoint tests.

    Provides a consistent user identity with both OpenFGA and Keycloak formats:
    - user_id: OpenFGA format with worker-safe ID for pytest-xdist isolation
    - keycloak_id: Keycloak UUID format
    - username: Plain username
    - email: User email
    """
    from tests.conftest import get_user_id

    return {
        "user_id": get_user_id("alice"),
        "keycloak_id": "8c7b4e5d-1234-5678-abcd-ef1234567890",
        "username": "alice",
        "email": "alice@example.com",
    }


@pytest.fixture
def mock_jwt_token():
    """
    Generate a mock JWT token with current timestamps.

    Uses datetime.now(UTC) to ensure token is always valid during test execution.
    """
    import jwt

    from tests.constants import TEST_JWT_EXPIRATION_HOURS

    NOW = datetime.now(UTC)

    payload = {
        "sub": "alice",
        "exp": NOW + timedelta(hours=TEST_JWT_EXPIRATION_HOURS),
        "iat": NOW,
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


@pytest.fixture(scope="session")
def mock_user_alice():
    """Mock user alice (session-scoped for performance)."""
    return {
        "username": "alice",
        "tier": "premium",
        "organization": "acme",
        "roles": ["admin", "user"],
    }


@pytest.fixture(scope="session")
def mock_user_bob():
    """Mock user bob (session-scoped for performance)."""
    return {
        "username": "bob",
        "tier": "standard",
        "organization": "acme",
        "roles": ["user"],
    }


@pytest.fixture(scope="session")
def register_mcp_test_users():
    """
    Register test users for MCP integration tests (session-scoped).

    Creates InMemoryUserProvider with pre-registered test users that match
    JWT tokens created by mock_jwt_token fixture.
    """
    from mcp_server_langgraph.auth.user_provider import InMemoryUserProvider

    provider = InMemoryUserProvider(secret_key=TEST_JWT_SECRET)

    provider.add_user(
        username="alice",
        password="test-password",
        email="alice@example.com",
        roles=["user", "admin"],
    )

    return provider
