"""
Tests for session-scoped test user registration fixture

Validates that test users are properly registered before MCP integration tests run.
This ensures consistent authentication state across all MCP tests.

Following TDD best practices:
- Tests define expected fixture behavior (RED phase)
- Fixture implementation makes tests pass (GREEN phase)
- Refactor for quality (REFACTOR phase)
"""

import pytest

from mcp_server_langgraph.auth.user_provider import InMemoryUserProvider
from tests.constants import TEST_JWT_SECRET

pytestmark = pytest.mark.integration


@pytest.mark.xdist_group(name="integration_mcp_test_user_tests")
class TestMCPTestUserRegistration:
    """Test that test users are properly registered for MCP tests"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        import gc

        gc.collect()

    @pytest.mark.asyncio
    async def test_register_mcp_test_users_fixture_exists(self, register_mcp_test_users):
        """
        Test that register_mcp_test_users fixture exists and is session-scoped.

        This fixture should:
        1. Be session-scoped (runs once per test session)
        2. Return a configured InMemoryUserProvider
        3. Have "alice" user pre-registered (for mock_jwt_token)

        TEST SHOULD FAIL until fixture is added to conftest.py (TDD RED phase).
        """
        # WHEN: Fixture is requested
        # THEN: It should return an InMemoryUserProvider instance
        assert isinstance(register_mcp_test_users, InMemoryUserProvider)

        # AND: Provider should use TEST_JWT_SECRET for consistency
        assert register_mcp_test_users.secret_key == TEST_JWT_SECRET

    @pytest.mark.asyncio
    async def test_alice_user_is_registered(self, register_mcp_test_users):
        """
        Test that "alice" user is pre-registered in the provider.

        The "alice" user is critical because mock_jwt_token fixture creates
        tokens with sub="alice". If alice isn't registered, auth fails.

        TEST SHOULD FAIL until fixture is added (TDD RED phase).
        """
        # GIVEN: The fixture provides a user provider
        provider = register_mcp_test_users

        # WHEN: We verify alice's credentials
        result = await provider.verify_password("alice", "test-password")

        # THEN: Alice should exist and credentials should verify
        assert result.valid is True
        assert result.user is not None
        assert result.user["username"] == "alice"

    @pytest.mark.asyncio
    async def test_alice_user_has_correct_attributes(self, register_mcp_test_users):
        """
        Test that "alice" user has expected attributes for integration tests.

        Attributes needed:
        - username: "alice" (matches JWT sub claim)
        - email: valid email format
        - roles: includes "user" role for basic permissions
        """
        # GIVEN: The fixture provides a user provider
        provider = register_mcp_test_users

        # WHEN: We verify alice's credentials
        result = await provider.verify_password("alice", "test-password")

        # THEN: User should have expected attributes
        assert result.valid is True
        user = result.user

        assert user["username"] == "alice"
        assert "email" in user
        assert "@" in user["email"]  # Valid email format
        assert "roles" in user
        assert "user" in user["roles"]  # Has basic user role

    @pytest.mark.asyncio
    async def test_fixture_is_session_scoped_shared_across_tests(
        self,
        register_mcp_test_users,
    ):
        """
        Test that fixture is session-scoped (same instance across tests).

        Session scope is critical for:
        1. Performance (don't recreate provider for each test)
        2. Consistency (same users across all tests)
        3. Memory efficiency (single provider instance)
        """
        # GIVEN: Fixture from first test
        provider1 = register_mcp_test_users

        # WHEN: We request it again in same session
        # (In practice, pytest caches session fixtures)
        provider2 = register_mcp_test_users

        # THEN: Should be the exact same instance (session-scoped)
        assert provider1 is provider2

        # AND: User should still be registered
        result = await provider1.verify_password("alice", "test-password")
        assert result.valid is True


@pytest.mark.xdist_group(name="integration_mcp_test_user_tests")
class TestMCPTestUserFixtureIntegration:
    """Test integration between user registration fixture and MCP server"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        import gc

        gc.collect()

    @pytest.mark.asyncio
    async def test_fixture_can_be_used_to_create_auth_middleware(
        self,
        register_mcp_test_users,
    ):
        """
        Test that fixture can be used to create AuthMiddleware for tests.

        This pattern allows test fixtures to inject the provider into auth:
        ```python
        @pytest.fixture
        async def mcp_server(register_mcp_test_users):
            auth = AuthMiddleware(user_provider=register_mcp_test_users, ...)
            return MCPAgentServer(auth=auth)
        ```
        """
        from unittest.mock import MagicMock

        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        # GIVEN: Provider from fixture with registered users
        provider = register_mcp_test_users

        # WHEN: We create AuthMiddleware with this provider
        auth = AuthMiddleware(
            secret_key=TEST_JWT_SECRET,
            user_provider=provider,
            openfga_client=None,
            session_store=None,
            settings=MagicMock(
                allow_auth_fallback=True,
                environment="test",
            ),
        )

        # THEN: Auth should use our provider
        assert auth.user_provider is provider

        # AND: Token verification should work for alice
        from datetime import datetime, timedelta, timezone

        import jwt

        payload = {
            "sub": "alice",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        }
        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")

        token_verification = await auth.verify_token(token)
        assert token_verification.valid is True
        assert token_verification.payload["sub"] == "alice"

        # AND: Authorization should work in fallback mode
        # (alice is registered, so fallback auth should succeed)
        authorized = await auth.authorize(
            user_id="alice",
            relation="executor",
            resource="tool:search_tools",
        )
        assert authorized is True

    @pytest.mark.asyncio
    async def test_multiple_test_users_can_be_registered(self, register_mcp_test_users):
        """
        Test that fixture can register multiple test users if needed.

        While "alice" is the primary test user (matches mock_jwt_token),
        tests may need additional users for multi-user scenarios.
        """
        # GIVEN: Provider from fixture
        provider = register_mcp_test_users

        # WHEN: We add another test user
        provider.add_user(
            username="bob",
            password="bob-password",
            email="bob@example.com",
            roles=["user"],
        )

        # THEN: Both users should be registered
        alice_result = await provider.verify_password("alice", "test-password")
        bob_result = await provider.verify_password("bob", "bob-password")

        assert alice_result.valid is True
        assert bob_result.valid is True
        assert alice_result.user["username"] == "alice"
        assert bob_result.user["username"] == "bob"
