"""
Unit tests for UserProvider.verify_password() method.

Tests verify that the verify_password method properly validates user credentials
and returns structured PasswordVerification responses with appropriate error handling.

Note: This module uses fresh imports inside each test method to avoid class identity
issues caused by importlib.reload() in other tests. When modules are reloaded,
isinstance() can fail because the class object identity changes.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


def _get_password_verification_class():
    """Get fresh PasswordVerification class to avoid reload identity issues."""
    from mcp_server_langgraph.auth.user_provider import PasswordVerification

    return PasswordVerification


def _get_inmemory_user_provider_class():
    """Get fresh InMemoryUserProvider class to avoid reload identity issues."""
    from mcp_server_langgraph.auth.user_provider import InMemoryUserProvider

    return InMemoryUserProvider


@pytest.mark.xdist_group(name="test_verify_password")
class TestUserProviderVerifyPassword:
    """Test verify_password functionality across UserProvider implementations"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def user_provider(self):
        """
        Create InMemoryUserProvider with test users.

        Provides a clean provider instance for each test.
        """
        from tests.conftest import get_user_id

        InMemoryUserProvider = _get_inmemory_user_provider_class()
        provider = InMemoryUserProvider(use_password_hashing=False)  # Plaintext for speed

        # Add test users with worker-safe IDs
        provider.users_db["alice"] = {
            "user_id": get_user_id("alice"),
            "email": "alice@example.com",
            "password": "alice-password",  # Plaintext (hashing disabled)
            "roles": ["user", "admin"],
            "active": True,
        }

        provider.users_db["bob"] = {
            "user_id": get_user_id("bob"),
            "email": "bob@example.com",
            "password": "bob-password",
            "roles": ["user"],
            "active": True,
        }

        return provider

    @pytest.mark.asyncio
    async def test_verify_password_success(self, user_provider):
        """
        Test successful password verification returns valid=True with user data.

        Expected behavior: Correct username + password returns structured response.
        """
        # WHEN: Verifying correct credentials
        result = await user_provider.verify_password("alice", "alice-password")

        # THEN: Verification should succeed with user data
        assert type(result).__name__ == "PasswordVerification", "Should return PasswordVerification object"
        assert result.valid is True, "Valid credentials should return valid=True"
        assert result.user is not None, "Valid credentials should include user data"
        assert result.error is None, "Successful verification should have no error"

        # AND: User data should be complete
        from tests.conftest import get_user_id

        assert result.user["username"] == "alice"
        assert result.user["user_id"] == get_user_id("alice")
        assert result.user["email"] == "alice@example.com"
        assert "admin" in result.user["roles"]

    @pytest.mark.asyncio
    async def test_verify_password_wrong_password(self, user_provider):
        """
        Test that wrong password returns valid=False with appropriate error.

        Security: Should not reveal whether username exists or password is wrong.
        Uses generic "Invalid credentials" message to prevent information disclosure.
        """
        # WHEN: Verifying with wrong password
        result = await user_provider.verify_password("alice", "wrong-password")

        # THEN: Verification should fail
        assert type(result).__name__ == "PasswordVerification"
        assert result.valid is False, "Wrong password should return valid=False"
        assert result.user is None, "Failed verification should not include user data"
        assert result.error is not None, "Failed verification should include error message"
        assert "invalid credentials" in result.error.lower(), "Error should use generic message"

    @pytest.mark.asyncio
    async def test_verify_password_nonexistent_user(self, user_provider):
        """
        Test that non-existent username returns valid=False.

        Security: Should not reveal whether username exists (timing attacks).
        """
        # WHEN: Verifying non-existent user
        result = await user_provider.verify_password("charlie", "any-password")

        # THEN: Verification should fail
        assert type(result).__name__ == "PasswordVerification"
        assert result.valid is False, "Non-existent user should return valid=False"
        assert result.user is None, "Failed verification should not include user data"
        assert result.error is not None, "Failed verification should include error message"

    @pytest.mark.asyncio
    async def test_verify_password_empty_username(self, user_provider):
        """
        Test that empty username is handled gracefully.

        Edge case: Empty string should not cause exceptions.
        """
        # WHEN: Verifying with empty username
        result = await user_provider.verify_password("", "any-password")

        # THEN: Should fail gracefully without exception
        assert type(result).__name__ == "PasswordVerification"
        assert result.valid is False
        assert result.user is None
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_verify_password_empty_password(self, user_provider):
        """
        Test that empty password is handled gracefully.

        Edge case: Empty password should fail validation.
        """
        # WHEN: Verifying with empty password
        result = await user_provider.verify_password("alice", "")

        # THEN: Should fail gracefully without exception
        assert type(result).__name__ == "PasswordVerification"
        assert result.valid is False
        assert result.user is None
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_verify_password_with_hashing_enabled(self):
        """
        Test verify_password respects password hashing settings.

        Uses bcrypt hashing for production-like testing.
        """
        # GIVEN: Provider with password hashing enabled
        from tests.conftest import get_user_id

        InMemoryUserProvider = _get_inmemory_user_provider_class()
        provider = InMemoryUserProvider(use_password_hashing=True)

        # Add user with hashed password
        import bcrypt

        hashed = bcrypt.hashpw(b"secure-password", bcrypt.gensalt())

        provider.users_db["secure-alice"] = {
            "user_id": get_user_id("secure-alice"),
            "email": "secure@example.com",
            "password": hashed.decode("utf-8"),
            "roles": ["user"],
            "active": True,
        }

        # WHEN: Verifying with correct password
        result = await provider.verify_password("secure-alice", "secure-password")

        # THEN: Should successfully verify hashed password
        assert result.valid is True
        assert result.user is not None
        assert result.user["username"] == "secure-alice"

        # AND: Wrong password should still fail
        result_wrong = await provider.verify_password("secure-alice", "wrong-password")
        assert result_wrong.valid is False

    @pytest.mark.asyncio
    async def test_verify_password_case_sensitive(self, user_provider):
        """
        Test that username comparison is case-sensitive.

        Security: Usernames should be treated as case-sensitive.
        """
        # WHEN: Verifying with different case
        result = await user_provider.verify_password("Alice", "alice-password")  # Capital A

        # THEN: Should fail (case-sensitive)
        assert result.valid is False
        assert result.user is None

    @pytest.mark.asyncio
    async def test_verify_password_multiple_users(self, user_provider):
        """
        Test that verify_password works correctly with multiple users.

        Ensures no cross-user contamination.
        """
        # WHEN: Verifying different users
        result_alice = await user_provider.verify_password("alice", "alice-password")
        result_bob = await user_provider.verify_password("bob", "bob-password")

        # THEN: Each should succeed with correct user data
        assert result_alice.valid is True
        assert result_alice.user["username"] == "alice"

        assert result_bob.valid is True
        assert result_bob.user["username"] == "bob"

        # AND: Cross-contamination should not occur
        result_alice_wrong = await user_provider.verify_password("alice", "bob-password")
        assert result_alice_wrong.valid is False

    @pytest.mark.asyncio
    async def test_password_verification_model_structure(self, user_provider):
        """
        Test that PasswordVerification model has expected structure.

        Ensures contract compliance for consumers.
        """
        # WHEN: Getting verification result
        result = await user_provider.verify_password("alice", "alice-password")

        # THEN: Model should have required attributes
        assert hasattr(result, "valid"), "PasswordVerification must have 'valid' attribute"
        assert hasattr(result, "user"), "PasswordVerification must have 'user' attribute"
        assert hasattr(result, "error"), "PasswordVerification must have 'error' attribute"

        # AND: Should be serializable
        result_dict = result.model_dump()
        assert "valid" in result_dict
        assert "user" in result_dict
        assert "error" in result_dict

    @pytest.mark.asyncio
    async def test_verify_password_does_not_modify_user_db(self, user_provider):
        """
        Test that verify_password is read-only (doesn't modify user database).

        Ensures verification doesn't have side effects.
        """
        # GIVEN: Initial user data
        original_user = user_provider.users_db["alice"].copy()

        # WHEN: Verifying password multiple times
        await user_provider.verify_password("alice", "alice-password")
        await user_provider.verify_password("alice", "wrong-password")
        await user_provider.verify_password("alice", "alice-password")

        # THEN: User data should remain unchanged
        assert user_provider.users_db["alice"] == original_user
