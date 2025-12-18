"""
Mock fixtures for unit testing.

Extracted from conftest.py as part of P1.3 Test Fixture Optimization.
Contains various mock fixtures for APIs, clients, and external services.
"""

from datetime import datetime, timedelta, UTC
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from langchain_core.messages import HumanMessage

from tests.constants import TEST_JWT_SECRET


# Check for optional dependencies
try:
    from freezegun import freeze_time

    FREEZEGUN_AVAILABLE = True
except ImportError:
    FREEZEGUN_AVAILABLE = False
    freeze_time = None


@pytest.fixture
def frozen_time():
    """
    Freeze time for deterministic timestamp testing.

    All datetime.now(), time.time(), etc. calls will return the fixed time.
    This eliminates test flakiness caused by time-dependent assertions.

    Usage:
        @pytest.mark.usefixtures("frozen_time")
        def test_timestamps():
            # datetime.now() will always return 2024-01-01T00:00:00Z
            assert datetime.now(timezone.utc).isoformat() == "2024-01-01T00:00:00+00:00"
    """
    if not FREEZEGUN_AVAILABLE:
        pytest.skip("freezegun not installed - required for time-freezing tests. Install with: pip install freezegun")

    with freeze_time("2024-01-01 00:00:00", tz_offset=0):
        yield


@pytest.fixture
def mock_app_settings():
    """
    Complete mock for app settings with all required attributes.

    Use this fixture when patching mcp_server_langgraph.app.settings
    to ensure auth factory validation passes.
    """
    mock = MagicMock()
    # Required for auth factory validation
    mock.auth_provider = "inmemory"
    mock.jwt_secret_key = "test-jwt-secret-key-for-testing"
    mock.environment = "development"
    mock.use_password_hashing = False
    # CORS settings
    mock.cors_allowed_origins = []
    mock.get_cors_origins = MagicMock(return_value=[])
    return mock


@pytest.fixture(scope="session")
def mock_openfga_response():
    """Mock OpenFGA API responses (session-scoped for performance)"""
    return {
        "check": {"allowed": True},
        "list_objects": {"objects": ["tool:chat", "tool:search"]},
        "write": {"writes": []},
        "read": {"tuples": [{"key": {"user": "user:alice", "relation": "executor", "object": "tool:chat"}}]},
    }


@pytest.fixture(scope="session")
def mock_infisical_response():
    """Mock Infisical API responses (session-scoped for performance)"""
    return {
        "secrets": [
            {"secretKey": "JWT_SECRET_KEY", "secretValue": "test-jwt-secret", "version": 1},
            {"secretKey": "ANTHROPIC_API_KEY", "secretValue": "sk-ant-test-key", "version": 1},
        ]
    }


@pytest.fixture
def mock_jwt_token():
    """
    Generate a mock JWT token with current timestamps.

    Uses datetime.now(UTC) to ensure token is always valid during test execution.
    Expiration is set to TEST_JWT_EXPIRATION_HOURS (1 hour) from now.

    IMPORTANT: Uses TEST_JWT_SECRET from tests/constants.py to ensure
    token signing matches server verification in all test environments.
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
    """Mock user alice (session-scoped for performance)"""
    return {
        "username": "alice",
        "tier": "premium",
        "organization": "acme",
        "roles": ["admin", "user"],
    }


@pytest.fixture(scope="session")
def mock_user_bob():
    """Mock user bob (session-scoped for performance)"""
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

    Returns:
        InMemoryUserProvider with "alice" user registered
    """
    from mcp_server_langgraph.auth.user_provider import InMemoryUserProvider

    # Create provider with TEST_JWT_SECRET for token verification
    provider = InMemoryUserProvider(secret_key=TEST_JWT_SECRET)

    # Register "alice" user (matches mock_jwt_token fixture sub claim)
    provider.add_user(
        username="alice",
        password="test-password",
        email="alice@example.com",
        roles=["user", "admin"],
    )

    return provider


@pytest.fixture
def mock_agent_state():
    """Mock LangGraph agent state"""
    return {
        "messages": [HumanMessage(content="Hello, what can you do?")],
        "next_action": "respond",
        "user_id": "alice",
        "request_id": "test-request-123",
    }


@pytest.fixture
async def mock_httpx_client():
    """Mock httpx async client"""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}
    mock_response.raise_for_status = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.get.return_value = mock_response

    return mock_client


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic API client"""
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="I am Claude, an AI assistant.")]
    mock_message.stop_reason = "end_turn"

    mock_client.messages.create.return_value = mock_message

    return mock_client


@pytest.fixture
async def mock_openfga_client(mock_openfga_response):
    """Mock OpenFGA client"""
    with patch("openfga_client.httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_openfga_response["check"]
        mock_response.raise_for_status = MagicMock()

        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance

        yield mock_client


@pytest.fixture
async def mock_infisical_client(mock_infisical_response):
    """Mock Infisical client"""
    with patch("mcp_server_langgraph.secret_providers.manager.InfisicalClient") as mock_client:
        mock_instance = MagicMock()
        mock_instance.get_secret.return_value = mock_infisical_response["secrets"][0]
        mock_instance.list_secrets.return_value = mock_infisical_response["secrets"]
        mock_client.return_value = mock_instance

        yield mock_client
