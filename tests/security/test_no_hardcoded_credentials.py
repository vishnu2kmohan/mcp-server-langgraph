"""
Security tests for hard-coded credentials removal (OpenAI Codex Finding #2)

SECURITY FINDING:
InMemoryUserProvider seeds fixed usernames/passwords (alice123, admin123) with
plaintext storage when bcrypt is absent. This test suite validates that:
1. No hard-coded credentials exist in the codebase
2. InMemoryUserProvider starts with empty user database
3. Users must be explicitly created via API or configuration
4. No default passwords exist in any code path

References:
- src/mcp_server_langgraph/auth/user_provider.py:348-367 (_init_users)
- CWE-798: Use of Hard-coded Credentials
"""

import ast
import re

import pytest

from mcp_server_langgraph.auth.user_provider import InMemoryUserProvider


@pytest.mark.security
@pytest.mark.unit
class TestNoHardcodedCredentials:
    """Test suite ensuring no hard-coded credentials exist"""

    def test_inmemory_provider_starts_with_empty_database(self):
        """
        SECURITY TEST: InMemoryUserProvider must start with empty user database

        No default users should be seeded. All users must be explicitly created.
        """
        provider = InMemoryUserProvider(use_password_hashing=False)

        # User database should be empty
        assert len(provider.users_db) == 0, (
            "SECURITY FAILURE: InMemoryUserProvider should start with empty user database, "
            f"but found {len(provider.users_db)} pre-seeded users: {list(provider.users_db.keys())}"
        )

    def test_no_alice_user_exists_by_default(self):
        """
        SECURITY TEST: No 'alice' user should exist by default

        This was one of the hard-coded credentials (alice/alice123) in the original code.
        """
        provider = InMemoryUserProvider(use_password_hashing=False)

        assert "alice" not in provider.users_db, (
            "SECURITY FAILURE: Hard-coded 'alice' user still exists in InMemoryUserProvider"
        )

    def test_no_bob_user_exists_by_default(self):
        """
        SECURITY TEST: No 'bob' user should exist by default

        This was one of the hard-coded credentials (bob/bob123) in the original code.
        """
        provider = InMemoryUserProvider(use_password_hashing=False)

        assert "bob" not in provider.users_db, (
            "SECURITY FAILURE: Hard-coded 'bob' user still exists in InMemoryUserProvider"
        )

    def test_no_admin_user_exists_by_default(self):
        """
        SECURITY TEST: No 'admin' user should exist by default

        This was one of the hard-coded credentials (admin/admin123) in the original code.
        """
        provider = InMemoryUserProvider(use_password_hashing=False)

        assert "admin" not in provider.users_db, (
            "SECURITY FAILURE: Hard-coded 'admin' user still exists in InMemoryUserProvider"
        )

    def test_users_can_be_created_explicitly(self):
        """
        Test that users can still be created explicitly via add_user() method

        This ensures the removal of hard-coded credentials doesn't break user creation.
        """
        provider = InMemoryUserProvider(use_password_hashing=False)

        # Explicitly create a test user
        provider.add_user(
            username="testuser",
            password="test-password-123",
            email="testuser@example.com",
            roles=["user"]
        )

        # User should now exist
        assert "testuser" in provider.users_db
        assert provider.users_db["testuser"]["email"] == "testuser@example.com"
        assert "user" in provider.users_db["testuser"]["roles"]

    def test_add_user_with_hashing_enabled(self):
        """
        Test that user creation works correctly with password hashing enabled
        """
        provider = InMemoryUserProvider(use_password_hashing=True)

        provider.add_user(
            username="hasheduser",
            password="secure-password",
            email="hasheduser@example.com",
            roles=["admin"]
        )

        # User should exist
        assert "hasheduser" in provider.users_db

        # Password should be hashed (bcrypt hashes start with $2b$)
        stored_password = provider.users_db["hasheduser"]["password"]
        assert stored_password.startswith("$2b$"), (
            "Password should be hashed with bcrypt"
        )
        assert stored_password != "secure-password", (
            "Password should not be stored in plaintext"
        )

    @pytest.mark.asyncio
    async def test_authentication_fails_without_users(self):
        """
        Test that authentication properly fails when no users exist

        This ensures the removal of default users doesn't cause crashes.
        """
        provider = InMemoryUserProvider(use_password_hashing=False)

        # Attempt to authenticate non-existent user
        result = await provider.authenticate("alice", "alice123")

        assert result.authorized is False
        assert result.reason == "invalid_credentials"

    @pytest.mark.asyncio
    async def test_authentication_succeeds_for_explicitly_created_user(self):
        """
        Test that authentication works for explicitly created users
        """
        provider = InMemoryUserProvider(use_password_hashing=False)

        # Create user explicitly
        provider.add_user(
            username="validuser",
            password="validpassword",
            email="validuser@example.com",
            roles=["user"]
        )

        # Authentication should succeed
        result = await provider.authenticate("validuser", "validpassword")

        assert result.authorized is True
        assert result.username == "validuser"
        assert "user" in result.roles


@pytest.mark.security
@pytest.mark.integration
class TestNoHardcodedCredentialsInSourceCode:
    """Static analysis tests to ensure no hard-coded credentials in source files"""

    def test_no_hardcoded_passwords_in_user_provider(self):
        """
        SECURITY TEST: Source code should not contain hard-coded password patterns

        Searches for common patterns like 'password123', 'alice123', etc.
        """
        import pathlib

        user_provider_file = pathlib.Path("src/mcp_server_langgraph/auth/user_provider.py")
        content = user_provider_file.read_text()

        # Patterns that indicate hard-coded credentials
        suspicious_patterns = [
            r'alice123',
            r'bob123',
            r'admin123',
            r'"password":\s*"[^"]*123"',  # password ending in 123
            r'default_users\s*=\s*\{',  # default_users dictionary
        ]

        for pattern in suspicious_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            assert len(matches) == 0, (
                f"SECURITY FAILURE: Found hard-coded credential pattern '{pattern}' "
                f"in user_provider.py: {matches}"
            )

    def test_no_init_users_method_exists(self):
        """
        SECURITY TEST: The _init_users() method that seeded default users should not exist

        This method was the source of hard-coded credentials.
        """
        import pathlib

        user_provider_file = pathlib.Path("src/mcp_server_langgraph/auth/user_provider.py")
        content = user_provider_file.read_text()

        # Check that _init_users method doesn't exist
        assert "_init_users" not in content, (
            "SECURITY FAILURE: The _init_users() method still exists in user_provider.py. "
            "This method seeds hard-coded credentials and should be removed."
        )

    def test_no_default_user_dictionary_in_source(self):
        """
        SECURITY TEST: No 'default_users' dictionary should exist in source code

        This was the data structure containing hard-coded credentials.
        """
        import pathlib

        user_provider_file = pathlib.Path("src/mcp_server_langgraph/auth/user_provider.py")

        try:
            tree = ast.parse(user_provider_file.read_text())
        except SyntaxError:
            pytest.skip("Could not parse user_provider.py")

        # Search for dictionary assignments named 'default_users'
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "default_users":
                        pytest.fail(
                            "SECURITY FAILURE: Found 'default_users' dictionary assignment "
                            f"at line {node.lineno}. Hard-coded credentials should not exist."
                        )


@pytest.mark.security
@pytest.mark.unit
class TestCredentialCreationDocumentation:
    """Tests to ensure proper documentation for creating test users"""

    def test_readme_contains_user_creation_example(self):
        """
        Test that README or documentation explains how to create test users

        Since we removed hard-coded credentials, developers need clear instructions.
        """
        import pathlib

        # Check README.md for user creation documentation
        readme_file = pathlib.Path("README.md")
        if not readme_file.exists():
            pytest.skip("README.md not found")

        content = readme_file.read_text()

        # Should mention user creation or InMemoryUserProvider
        has_user_creation_docs = any([
            "add_user" in content,
            "create user" in content.lower(),
            "inmemoryprovider" in content.lower(),
            "test users" in content.lower(),
        ])

        assert has_user_creation_docs, (
            "README.md should document how to create test users now that "
            "hard-coded credentials have been removed"
        )

    def test_add_user_method_has_docstring(self):
        """
        Test that the add_user() method has proper documentation

        This is the recommended way to create users for testing.
        """
        # Check that add_user method is documented
        assert InMemoryUserProvider.add_user.__doc__ is not None, (
            "The add_user() method should have a docstring explaining how to use it"
        )

        docstring = InMemoryUserProvider.add_user.__doc__
        assert "username" in docstring.lower()
        assert "password" in docstring.lower()
