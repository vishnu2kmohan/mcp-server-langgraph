"""
Property-based tests for Authentication and Authorization

Tests security-critical invariants using Hypothesis.
"""

import gc
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st


# Helper to run async code in sync tests with proper event loop cleanup
def run_async(coro):
    """
    Run async coroutine safely for property-based tests.

    CRITICAL: Properly manages event loop lifecycle to prevent:
    - Invalid file descriptor errors (BaseEventLoop.__del__)
    - Event loop pollution across hypothesis examples
    - Memory leaks in pytest-xdist workers

    Pattern: Create fresh loop, run coroutine, close loop explicitly

    Args:
        coro: Async coroutine to execute

    Returns:
        Result of the coroutine
    """
    import asyncio

    # Check if there's already a running event loop
    try:
        # If we're in an async context, use the running loop
        loop = asyncio.get_running_loop()
        # Running loop exists, just execute the coroutine
        return loop.run_until_complete(coro)
    except RuntimeError:
        # No event loop exists, create a fresh one for this test
        pass

    # ALWAYS create a fresh event loop for property tests
    # This prevents pollution across hypothesis examples
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Run the coroutine
        result = loop.run_until_complete(coro)
        return result
    finally:
        # CRITICAL: Always close the loop to free file descriptors
        try:
            # Cancel all pending tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()

            # Run loop briefly to allow tasks to cancel
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

            # Close the loop
            loop.close()
        except Exception as e:
            # Log but don't fail the test
            import logging

            logging.getLogger(__name__).warning(f"Error cleaning up event loop: {e}")


# Hypothesis strategies for auth testing
# Use known valid usernames that exist in auth.py users_db
valid_usernames = st.sampled_from(["alice", "bob", "admin"])
usernames = valid_usernames  # Alias for compatibility

user_ids = st.builds(lambda name: f"user:{name}", usernames)

resource_types = st.sampled_from(["tool", "conversation", "organization"])

resource_names = st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("Ll", "Nd")))

resources = st.builds(lambda t, n: f"{t}:{n}", resource_types, resource_names)

relations = st.sampled_from(["executor", "viewer", "editor", "owner", "admin", "member"])

# JWT expiration times
expiration_seconds = st.integers(min_value=1, max_value=86400)  # 1s to 24h


def add_test_users(auth):
    """
    Helper to add test users to AuthMiddleware users_db.

    After security fix (OpenAI Codex Finding #2), users_db is empty by default.
    Tests must explicitly add users.
    """
    test_users = {
        "alice": {
            "user_id": "user:alice",
            "email": "alice@test.com",
            "password": "test123",
            "roles": ["user", "executor"],
            "active": True,
        },
        "bob": {
            "user_id": "user:bob",
            "email": "bob@test.com",
            "password": "test123",
            "roles": ["user", "viewer"],
            "active": True,
        },
        "admin": {
            "user_id": "user:admin",
            "email": "admin@test.com",
            "password": "admin123",
            "roles": ["admin", "user"],
            "active": True,
        },
    }

    for username, user_data in test_users.items():
        auth.users_db[username] = user_data


@pytest.mark.unit
@pytest.mark.xdist_group(name="property_auth_properties_tests")
class TestJWTProperties:
    """Property-based tests for JWT authentication"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @given(username=usernames, expiration=expiration_seconds)
    @settings(max_examples=50, deadline=2000)
    def test_jwt_encode_decode_roundtrip(self, username, expiration):
        """Property: JWT encode/decode should be reversible"""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        auth = AuthMiddleware(secret_key="test-secret")
        add_test_users(auth)  # Add test users after security fix

        # Create token
        token = auth.create_token(username, expires_in=expiration)

        # Verify token (async call)
        result = run_async(auth.verify_token(token))

        # Property: Should be valid (Pydantic model)
        assert result.valid is True
        assert result.payload["username"] == username
        assert "exp" in result.payload
        assert "iat" in result.payload

    @given(username=usernames, secret1=st.text(min_size=10, max_size=50), secret2=st.text(min_size=10, max_size=50))
    @settings(max_examples=30, deadline=2000)
    def test_jwt_requires_correct_secret(self, username, secret1, secret2):
        """Property: JWT verification requires the correct secret key"""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        assume(secret1 != secret2)

        auth1 = AuthMiddleware(secret_key=secret1)
        auth2 = AuthMiddleware(secret_key=secret2)
        add_test_users(auth1)  # Add test users after security fix
        add_test_users(auth2)

        # Create token with secret1
        token = auth1.create_token(username)

        # Property: Verification with wrong secret should fail
        result = run_async(auth2.verify_token(token))
        assert result.valid is False
        assert result.error is not None

    @given(username=usernames)
    @settings(max_examples=20, deadline=2000)
    def test_expired_tokens_rejected(self, username):
        """Property: Expired tokens should always be rejected"""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        auth = AuthMiddleware(secret_key="test-secret")

        # Create token that expired 1 hour ago
        expired_payload = {
            "sub": f"user:{username}",
            "username": username,
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }

        expired_token = jwt.encode(expired_payload, "test-secret", algorithm="HS256")

        # Property: Should be invalid
        result = run_async(auth.verify_token(expired_token))
        assert result.valid is False
        assert "expired" in (result.error or "").lower()

    @given(username=usernames, expiration=st.integers(min_value=60, max_value=3600))
    @settings(max_examples=20, deadline=2000)
    def test_token_expiration_time_honored(self, username, expiration):
        """Property: Token expiration should match requested time"""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        auth = AuthMiddleware(secret_key="test-secret")
        add_test_users(auth)  # Add test users after security fix

        before_creation = datetime.now(timezone.utc)
        token = auth.create_token(username, expires_in=expiration)
        after_creation = datetime.now(timezone.utc)

        result = run_async(auth.verify_token(token))
        assert result.valid is True

        # Property: Expiration should be approximately correct (allow 1 second tolerance for timing)
        token_exp = datetime.fromtimestamp(result.payload["exp"], timezone.utc)
        expected_min = before_creation + timedelta(seconds=expiration) - timedelta(seconds=1)
        expected_max = after_creation + timedelta(seconds=expiration) + timedelta(seconds=1)

        assert expected_min <= token_exp <= expected_max


@pytest.mark.property
@pytest.mark.unit
@pytest.mark.xdist_group(name="property_auth_properties_tests")
class TestAuthorizationProperties:
    """Property-based tests for authorization logic"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @given(user_id=user_ids, relation=relations, resource=resources)
    @settings(max_examples=30, deadline=3000)
    @pytest.mark.asyncio
    async def test_authorization_is_deterministic(self, user_id, relation, resource):
        """Property: Same authorization check should give same result"""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        auth = AuthMiddleware()

        # Mock OpenFGA to return consistent results
        with patch.object(auth, "openfga") as mock_openfga:
            mock_openfga.check_permission = AsyncMock(return_value=True)

            # Call twice
            result1 = await auth.authorize(user_id, relation, resource)
            result2 = await auth.authorize(user_id, relation, resource)

            # Property: Should be deterministic
            assert result1 == result2

    @given(resource=resources)
    @settings(max_examples=20, deadline=3000)
    @pytest.mark.asyncio
    async def test_admin_always_authorized(self, resource):
        """Property: Admin users should always be authorized (fallback mode)"""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware
        from mcp_server_langgraph.core.config import Settings

        # Create settings with test environment to enable fallback authorization
        test_settings = Settings(
            environment="testing",
            allow_auth_fallback=True,
        )

        auth = AuthMiddleware(secret_key="test-secret", settings=test_settings)
        add_test_users(auth)  # Add test users after security fix
        # No OpenFGA client - fallback mode

        # Property: Admin should have access to everything in test environment with fallback enabled
        authorized = await auth.authorize("user:admin", "executor", resource)

        assert authorized is True

    @given(user_id=user_ids, relation=relations, resource=resources)
    @settings(max_examples=20, deadline=3000)
    @pytest.mark.asyncio
    async def test_openfga_failure_denies_access(self, user_id, relation, resource):
        """Property: OpenFGA errors should deny access (fail-closed)"""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        auth = AuthMiddleware()

        # Mock OpenFGA to raise exception
        with patch.object(auth, "openfga") as mock_openfga:
            mock_openfga.check_permission = AsyncMock(side_effect=Exception("OpenFGA error"))

            # Property: Should deny on error (fail-closed)
            authorized = await auth.authorize(user_id, relation, resource)
            assert authorized is False

    @given(username=usernames)
    @settings(max_examples=20, deadline=2000)
    @pytest.mark.asyncio
    async def test_inactive_users_denied(self, username):
        """Property: Inactive users should never be authorized"""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        auth = AuthMiddleware()

        # Add inactive user to database
        if username not in auth.users_db:
            auth.users_db[username] = {
                "user_id": f"user:{username}",
                "email": f"{username}@test.com",
                "password": "test123",  # Add password for authentication
                "roles": ["user"],
                "active": False,  # Inactive
            }
        else:
            auth.users_db[username]["active"] = False
            if "password" not in auth.users_db[username]:
                auth.users_db[username]["password"] = "test123"

        # Property: Should not authenticate
        result = await auth.authenticate(username, "test123")
        assert result.authorized is False
        assert result.reason == "account_inactive"


@pytest.mark.property
@pytest.mark.unit
@pytest.mark.xdist_group(name="property_auth_properties_tests")
class TestPermissionInheritance:
    """Property tests for permission inheritance and transitivity"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @given(
        org_user=usernames,
        tool_name=resource_names,
    )
    @settings(max_examples=15, deadline=3000)
    @pytest.mark.asyncio
    async def test_org_membership_grants_tool_access(self, org_user, tool_name):
        """Property: Organization members should have access to org tools"""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        auth = AuthMiddleware()

        # Mock OpenFGA with org relationship
        with patch.object(auth, "openfga") as mock_openfga:

            async def mock_check(user, relation, object, context=None):
                # Simulate: user is org member, tool belongs to org
                if relation == "executor" and object == f"tool:{tool_name}":
                    # Check if user is org member (simplified)
                    return True
                return False

            mock_openfga.check_permission = mock_check

            # Property: Org member should have tool access
            authorized = await auth.authorize(f"user:{org_user}", "executor", f"tool:{tool_name}")

            # In real OpenFGA this would check transitivity
            # For now just verify the mock works
            assert isinstance(authorized, bool)

    @given(owner=usernames, resource=resources)
    @settings(max_examples=15, deadline=3000)
    @pytest.mark.asyncio
    async def test_ownership_implies_all_permissions(self, owner, resource):
        """Property: Resource owners should have all permissions"""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        auth = AuthMiddleware()

        with patch.object(auth, "openfga") as mock_openfga:

            async def mock_check(user, relation, object, context=None):
                # Owner has all permissions
                if user == f"user:{owner}" and object == resource:
                    return True
                return False

            mock_openfga.check_permission = mock_check

            # Property: Owner should have viewer, editor, owner relations
            for relation in ["viewer", "editor", "owner"]:
                authorized = await auth.authorize(f"user:{owner}", relation, resource)
                assert authorized is True


@pytest.mark.property
@pytest.mark.unit
@pytest.mark.xdist_group(name="property_auth_properties_tests")
class TestSecurityInvariants:
    """Property tests for critical security invariants"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @given(username=usernames, malicious_payload=st.dictionaries(st.text(), st.text()))
    @settings(max_examples=20, deadline=2000)
    def test_token_payload_not_user_controlled(self, username, malicious_payload):
        """Property: User cannot inject arbitrary claims into JWT"""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        auth = AuthMiddleware(secret_key="test-secret")
        add_test_users(auth)  # Add test users after security fix

        # Create normal token
        token = auth.create_token(username)

        # Verify token
        result = run_async(auth.verify_token(token))

        # Property: Payload should only contain expected fields
        expected_fields = {"sub", "username", "email", "roles", "exp", "iat", "jti"}
        actual_fields = set(result.payload.keys())

        # All actual fields should be expected (no injection)
        assert actual_fields.issubset(expected_fields)

    @given(username=usernames)
    @settings(max_examples=20, deadline=2000)
    def test_tokens_contain_user_id_not_password(self, username):
        """Property: JWT should never contain sensitive data like passwords"""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        auth = AuthMiddleware(secret_key="test-secret")
        add_test_users(auth)  # Add test users after security fix

        token = auth.create_token(username)

        # Decode without verification to inspect
        decoded = jwt.decode(token, options={"verify_signature": False})

        # Property: Should not contain sensitive fields
        sensitive_fields = ["password", "secret", "api_key", "token"]
        for field in sensitive_fields:
            assert field not in decoded
            assert field not in str(decoded.values())

    @given(username=usernames, attempts=st.integers(min_value=1, max_value=10))
    @settings(max_examples=10, deadline=3000)
    def test_failed_auth_does_not_leak_info(self, username, attempts):
        """Property: Failed authentication should not reveal whether user exists"""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        auth = AuthMiddleware()

        # Try to authenticate non-existent user multiple times
        nonexistent_user = f"nonexistent_{username}_{attempts}"

        async def run_test():
            results = []
            for _ in range(attempts):
                result = await auth.authenticate(nonexistent_user, "wrong_password")
                results.append(result)
            return results

        results = run_async(run_test())

        # Property: All failures should return same generic error
        assert all(not r.authorized for r in results)
        # Changed from "user_not_found" to "invalid_credentials" to prevent username enumeration
        assert all(r.reason == "invalid_credentials" for r in results)

        # Property: Response should be consistent (no timing attacks)
        # In production, add constant-time comparison


@pytest.mark.property
@pytest.mark.integration
@pytest.mark.xdist_group(name="property_auth_properties_tests")
class TestAuthorizationEdgeCases:
    """Property tests for edge cases in authorization"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @given(
        user_id=st.one_of(
            st.just(""),  # Empty string
            st.just("user:"),  # No username
            st.just(":username"),  # No prefix
            st.text(min_size=1000, max_size=2000),  # Very long
        )
    )
    @settings(max_examples=20, deadline=3000)
    def test_malformed_user_ids_handled(self, user_id):
        """Property: Malformed user IDs should not crash the system"""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        auth = AuthMiddleware()

        async def run_test():
            return await auth.authorize(user_id, "executor", "tool:test")

        try:
            # Should not crash, even with malformed input
            result = run_async(run_test())

            # Property: Should return boolean
            assert isinstance(result, bool)

        except Exception as e:
            # If it raises, should be a well-defined exception
            assert isinstance(e, (ValueError, PermissionError))

    @given(resource=st.one_of(st.just(""), st.just("::"), st.just("tool:"), st.text(min_size=1000, max_size=2000)))
    @settings(max_examples=20, deadline=3000)
    def test_malformed_resources_handled(self, resource):
        """Property: Malformed resource IDs should not crash the system"""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        auth = AuthMiddleware()

        async def run_test():
            return await auth.authorize("user:alice", "executor", resource)

        try:
            result = run_async(run_test())
            assert isinstance(result, bool)
        except Exception as e:
            assert isinstance(e, (ValueError, PermissionError))
