"""
Integration tests for MCPAgentServer constructor-based dependency injection

Tests the pattern of injecting pre-configured AuthMiddleware into MCPAgentServer.
This allows tests to configure authentication properly before server initialization.

Following TDD best practices:
- These tests define the desired API (RED phase)
- Implementation follows to make tests pass (GREEN phase)
- Then refactor for quality (REFACTOR phase)
"""

import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.auth.user_provider import InMemoryUserProvider
from mcp_server_langgraph.mcp.server_stdio import MCPAgentServer
from tests.constants import TEST_JWT_SECRET

pytestmark = [pytest.mark.integration, pytest.mark.mcp, pytest.mark.auth]


@pytest.mark.xdist_group(name="integration_mcp_auth_injection_tests")
class TestMCPServerAuthInjection:
    """Test MCPAgentServer with constructor-injected AuthMiddleware"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_server_accepts_injected_auth_middleware(self):
        """
        Test that MCPAgentServer accepts AuthMiddleware via constructor.

        This is the desired API pattern that enables proper dependency injection.
        TEST SHOULD FAIL until implementation is added (TDD RED phase).
        """
        # GIVEN: A user provider with registered test user
        user_provider = InMemoryUserProvider(secret_key=TEST_JWT_SECRET)
        user_provider.add_user(
            username="alice",
            password="test-password",
            email="alice@example.com",
            roles=["user"],
        )

        # AND: Auth middleware configured with that provider
        auth = AuthMiddleware(
            secret_key=TEST_JWT_SECRET,
            user_provider=user_provider,
            openfga_client=None,
            session_store=None,
            settings=MagicMock(
                allow_auth_fallback=True,
                environment="test",
            ),
        )

        # WHEN: Server is created with injected auth
        server = MCPAgentServer(auth=auth)

        # THEN: Server should use the injected auth instance
        assert server.auth is auth
        assert server.auth.user_provider is user_provider

        # AND: The user provider should have our test user
        # This verifies the injection worked - we're using the same instance
        verification = await user_provider.verify_password("alice", "test-password")
        assert verification.valid is True

    @pytest.mark.asyncio
    async def test_server_with_injected_auth_allows_tool_calls(self, mock_jwt_token):
        """
        Test that tool calls succeed when auth is properly injected with registered users.

        This is the INTEGRATION test that verifies the full auth flow works.
        TEST SHOULD FAIL until implementation is added (TDD RED phase).
        """
        # GIVEN: A user provider with "alice" registered (matches mock_jwt_token fixture)
        user_provider = InMemoryUserProvider(secret_key=TEST_JWT_SECRET)
        user_provider.add_user(
            username="alice",
            password="test-password",
            email="alice@example.com",
            roles=["user"],
        )

        # AND: Auth middleware with fallback enabled
        auth = AuthMiddleware(
            secret_key=TEST_JWT_SECRET,
            user_provider=user_provider,
            openfga_client=None,
            session_store=None,
            settings=MagicMock(
                allow_auth_fallback=True,
                environment="test",
            ),
        )

        # WHEN: Server is created with this auth
        server = MCPAgentServer(auth=auth)

        # THEN: Tool calls should succeed (auth flow: verify token → check user exists → authorize)
        # Note: search_tools is a read-only tool that should pass authorization
        result = await server.call_tool_public(
            name="search_tools",
            arguments={"category": "calculator", "detail_level": "minimal", "token": mock_jwt_token},
        )

        # Should return calculator tools
        result_str = str(result)
        assert "calculator" in result_str.lower() or "Found 0" in result_str

    @pytest.mark.asyncio
    async def test_server_without_injected_auth_creates_default(self):
        """
        Test backward compatibility: server without injected auth creates its own.

        This ensures existing code continues to work (no breaking changes).
        """
        # WHEN: Server is created without auth parameter (backward compatible)
        server = MCPAgentServer()

        # THEN: Server should have created its own auth instance
        assert server.auth is not None
        assert isinstance(server.auth, AuthMiddleware)

        # AND: Auth should have a user provider (even if empty)
        assert server.auth.user_provider is not None

    @pytest.mark.asyncio
    async def test_server_prioritizes_injected_auth_over_default(self):
        """
        Test that injected auth takes precedence over default creation.

        This ensures explicit injection overrides default behavior.
        """
        # GIVEN: A custom auth instance with specific user provider
        custom_provider = InMemoryUserProvider(secret_key="custom-secret")
        custom_provider.add_user(
            username="custom-user",
            password="custom-pass",
            email="custom@example.com",
            roles=["custom"],
        )

        custom_auth = AuthMiddleware(
            secret_key="custom-secret",
            user_provider=custom_provider,
            openfga_client=None,
            session_store=None,
            settings=MagicMock(
                allow_auth_fallback=True,
                environment="test",
            ),
        )

        # WHEN: Server is created with injected auth
        server = MCPAgentServer(auth=custom_auth)

        # THEN: Server should use the injected auth, not create its own
        assert server.auth is custom_auth
        assert server.auth.user_provider is custom_provider

        # Verify by checking for custom user
        verification = await custom_provider.verify_password("custom-user", "custom-pass")
        assert verification.valid is True


@pytest.mark.xdist_group(name="integration_mcp_auth_injection_tests")
class TestMCPServerAuthInjectionWithOpenfga:
    """Test MCPAgentServer auth injection with OpenFGA client"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.asyncio
    async def test_server_accepts_both_auth_and_openfga(self):
        """
        Test that server can accept both auth middleware AND openfga client.

        This tests backward compatibility with existing openfga_client parameter.
        """
        # GIVEN: A custom auth instance
        custom_auth = AuthMiddleware(
            secret_key=TEST_JWT_SECRET,
            user_provider=InMemoryUserProvider(secret_key=TEST_JWT_SECRET),
            openfga_client=None,
            session_store=None,
            settings=MagicMock(allow_auth_fallback=True, environment="test"),
        )

        # AND: A mock OpenFGA client
        mock_openfga = MagicMock()

        # WHEN: Server is created with both parameters
        server = MCPAgentServer(auth=custom_auth, openfga_client=mock_openfga)

        # THEN: Server should use injected auth
        assert server.auth is custom_auth

        # AND: Server should use injected OpenFGA client
        assert server.openfga is mock_openfga
