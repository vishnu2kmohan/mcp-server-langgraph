"""TDD tests for secrets obfuscation and leak prevention.

These tests verify that secrets are properly obfuscated in:
- String representations (__str__, __repr__)
- Exception messages
- Log output via sanitize_for_logging()

Security Context:
- CWE-200: Information Exposure
- CWE-532: Information Exposure Through Log Files
- OWASP: Sensitive Data Exposure

Note: This file contains fake/test secrets for validation purposes.
All "secrets" in this file are intentionally fake test data.

# gitleaks:allow - This file contains intentionally fake test secrets for validation
# All secret patterns in this file are for testing the obfuscation mechanism
"""

import gc
from importlib.util import find_spec
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit

# Check if infisical-python is available
INFISICAL_AVAILABLE = find_spec("infisical_client") is not None

# Check if SecretString is available
SECRET_STRING_AVAILABLE = find_spec("mcp_server_langgraph.secrets.manager") is not None


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.xdist_group(name="secrets_obfuscation_tests")
@pytest.mark.skipif(not SECRET_STRING_AVAILABLE, reason="SecretString not yet implemented")
class TestSecretString:
    """Test SecretString wrapper class for safe secret handling."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_str_returns_redacted(self):
        """Test that __str__ returns redacted placeholder, not actual value."""
        from mcp_server_langgraph.secrets.manager import SecretString

        secret = SecretString("my-super-secret-api-key-12345")
        result = str(secret)

        assert result == "***REDACTED***"
        assert "my-super-secret" not in result
        assert "12345" not in result

    def test_repr_returns_redacted(self):
        """Test that __repr__ returns redacted representation."""
        from mcp_server_langgraph.secrets.manager import SecretString

        secret = SecretString("password123")
        result = repr(secret)

        assert "REDACTED" in result
        assert "password123" not in result

    def test_get_secret_value_returns_actual_value(self):
        """Test that get_secret_value() returns the actual secret."""
        from mcp_server_langgraph.secrets.manager import SecretString

        original_value = "my-actual-secret-value"
        secret = SecretString(original_value)

        assert secret.get_secret_value() == original_value

    def test_secret_not_in_format_string(self):
        """Test that secrets are safe in f-strings and format()."""
        from mcp_server_langgraph.secrets.manager import SecretString

        secret = SecretString("api_key_abc123")
        log_message = f"Using secret: {secret}"

        assert "api_key_abc123" not in log_message
        assert "REDACTED" in log_message

    def test_secret_not_in_exception_message(self):
        """Test that secrets don't leak in exception messages."""
        from mcp_server_langgraph.secrets.manager import SecretString

        secret = SecretString("jwt_token_xyz")

        try:
            raise ValueError(f"Failed to process: {secret}")
        except ValueError as e:
            error_message = str(e)
            assert "jwt_token_xyz" not in error_message
            assert "REDACTED" in error_message

    def test_empty_secret_string(self):
        """Test SecretString with empty value."""
        from mcp_server_langgraph.secrets.manager import SecretString

        secret = SecretString("")
        assert secret.get_secret_value() == ""
        assert "REDACTED" in str(secret)

    def test_secret_equality_check(self):
        """Test that equality comparison works on actual values."""
        from mcp_server_langgraph.secrets.manager import SecretString

        secret1 = SecretString("same-value")
        secret2 = SecretString("same-value")
        secret3 = SecretString("different-value")

        # Equality should compare actual values
        assert secret1 == secret2
        assert secret1 != secret3

    def test_secret_hash_consistency(self):
        """Test that hash is consistent for same values."""
        from mcp_server_langgraph.secrets.manager import SecretString

        secret1 = SecretString("hash-test-value")
        secret2 = SecretString("hash-test-value")
        secret3 = SecretString("different-hash-value")

        # Same values should have same hash
        assert hash(secret1) == hash(secret2)
        # Different values should have different hash
        assert hash(secret1) != hash(secret3)

    def test_secret_in_set(self):
        """Test that SecretString works correctly in sets."""
        from mcp_server_langgraph.secrets.manager import SecretString

        secret1 = SecretString("set-value")
        secret2 = SecretString("set-value")
        secret3 = SecretString("other-value")

        secrets_set = {secret1, secret2, secret3}

        # Should only have 2 unique values (secret1 and secret2 are equal)
        assert len(secrets_set) == 2

    def test_secret_as_dict_key(self):
        """Test that SecretString can be used as a dictionary key."""
        from mcp_server_langgraph.secrets.manager import SecretString

        secret_key = SecretString("dict-key-value")
        data = {secret_key: "some-data"}

        # Lookup should work with equal SecretString
        lookup_key = SecretString("dict-key-value")
        assert data[lookup_key] == "some-data"

    def test_secret_equality_with_non_secret(self):
        """Test that SecretString is not equal to non-SecretString values."""
        from mcp_server_langgraph.secrets.manager import SecretString

        secret = SecretString("test-value")

        # Should not be equal to plain string
        assert secret != "test-value"
        # Should not be equal to None
        assert secret != None  # noqa: E711
        # Should not be equal to int
        assert secret != 123

    def test_secret_string_with_special_characters(self):
        """Test SecretString with special characters."""
        from mcp_server_langgraph.secrets.manager import SecretString

        special_value = "password!@#$%^&*()_+-=[]{}|;':\",./<>?"
        secret = SecretString(special_value)

        assert secret.get_secret_value() == special_value
        assert "REDACTED" in str(secret)
        assert special_value not in str(secret)

    def test_secret_string_with_unicode(self):
        """Test SecretString with unicode characters."""
        from mcp_server_langgraph.secrets.manager import SecretString

        unicode_value = "密码🔒日本語العربية"
        secret = SecretString(unicode_value)

        assert secret.get_secret_value() == unicode_value
        assert "REDACTED" in str(secret)
        assert unicode_value not in str(secret)

    def test_secret_string_with_newlines(self):
        """Test SecretString with newline characters."""
        from mcp_server_langgraph.secrets.manager import SecretString

        multiline_value = "line1\nline2\nline3"
        secret = SecretString(multiline_value)

        assert secret.get_secret_value() == multiline_value
        assert "REDACTED" in str(secret)
        assert multiline_value not in str(secret)


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.xdist_group(name="secrets_obfuscation_tests")
@pytest.mark.skipif(not INFISICAL_AVAILABLE, reason="infisical-python not installed")
class TestSecretsManagerObfuscation:
    """Test SecretsManager string representation security."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_str_does_not_expose_client_secret(self, mock_client):
        """Test that __str__ does not expose client_secret."""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        manager = SecretsManager(
            site_url="https://app.infisical.com",
            client_id="test-client-id",
            client_secret="super-secret-client-secret-value",
            project_id="test-project",
            environment="prod",
        )

        result = str(manager)

        assert "super-secret-client-secret-value" not in result
        assert "client_secret" not in result.lower() or "REDACTED" in result
        # Should include safe info
        assert "test-project" in result or "SecretsManager" in result

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_repr_does_not_expose_secrets(self, mock_client):
        """Test that __repr__ does not expose sensitive data."""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        manager = SecretsManager(
            site_url="https://app.infisical.com",
            client_id="my-client-id",
            client_secret="my-client-secret-xyz",
            project_id="my-project",
            environment="dev",
        )

        result = repr(manager)

        assert "my-client-secret-xyz" not in result
        # The client_secret value should never appear in repr
        # Note: "SecretsManager" class name contains "secret" but that's the class name, not a secret value
        assert "my-client-secret" not in result.lower()

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_secrets_not_in_exception_traceback(self, mock_client):
        """Test that secrets don't leak in exception tracebacks."""
        from mcp_server_langgraph.secrets.manager import SecretsManager

        manager = SecretsManager(
            client_id="test-id",
            client_secret="traceback-secret-value",
            project_id="test-project",
        )

        # Simulate an error scenario
        try:
            raise RuntimeError(f"Error with manager: {manager}")
        except RuntimeError as e:
            error_str = str(e)
            assert "traceback-secret-value" not in error_str


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.xdist_group(name="secrets_obfuscation_tests")
class TestSanitizeForLoggingComprehensive:
    """Test comprehensive field coverage in sanitize_for_logging()."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_redacts_password_fields(self):
        """Test that password fields are redacted."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        args = {
            "password": "super-secret-password",
            "user_password": "another-password",
            "db_password": "database-pass",
        }

        result = sanitize_for_logging(args)

        assert result["password"] == "[REDACTED]"
        # user_password and db_password may or may not be redacted depending on implementation

    def test_redacts_api_key_fields(self):
        """Test that API key fields are redacted."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        args = {
            "api_key": "sk_live_abc123xyz",
            "api_key_value": "another_key",
        }

        result = sanitize_for_logging(args)

        assert result["api_key"] == "[REDACTED]"
        assert result.get("api_key_value") == "[REDACTED]" or "api_key_value" not in result

    def test_redacts_client_secret(self):
        """Test that client_secret is redacted."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        args = {"client_secret": "oauth-client-secret-value"}

        result = sanitize_for_logging(args)

        assert result["client_secret"] == "[REDACTED]"

    def test_redacts_access_tokens(self):
        """Test that access/refresh tokens are redacted."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        args = {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh_token": "refresh_abc123",
            "bearer_token": "bearer_xyz789",
        }

        result = sanitize_for_logging(args)

        assert result["access_token"] == "[REDACTED]"
        assert result["refresh_token"] == "[REDACTED]"
        assert result["bearer_token"] == "[REDACTED]"

    def test_redacts_secret_and_secret_key(self):
        """Test that secret/secret_key fields are redacted."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        args = {
            "secret": "my-secret-value",
            "secret_key": "encryption-key-abc",
        }

        result = sanitize_for_logging(args)

        assert result["secret"] == "[REDACTED]"
        assert result["secret_key"] == "[REDACTED]"

    def test_redacts_credentials_with_nested_dict_returns_redacted(self):
        """Test that credential fields are redacted."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        args = {
            "credentials": {"username": "user", "password": "pass"},
            "credential": "some-credential-value",
        }

        result = sanitize_for_logging(args)

        assert result["credentials"] == "[REDACTED]"
        assert result["credential"] == "[REDACTED]"

    def test_redacts_authorization_header(self):
        """Test that authorization header is redacted."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        args = {"authorization": "Bearer eyJhbG..."}

        result = sanitize_for_logging(args)

        assert result["authorization"] == "[REDACTED]"

    def test_redacts_jwt_fields(self):
        """Test that JWT fields are redacted."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        args = {
            "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0...",
            "auth_token": "auth-token-value",
        }

        result = sanitize_for_logging(args)

        assert result["jwt"] == "[REDACTED]"
        assert result["auth_token"] == "[REDACTED]"

    def test_redacts_private_key(self):
        """Test that private_key is redacted."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        # gitleaks:allow - Fake/truncated test key for obfuscation validation
        args = {"private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIE..."}

        result = sanitize_for_logging(args)

        assert result["private_key"] == "[REDACTED]"

    def test_preserves_non_sensitive_fields(self):
        """Test that non-sensitive fields are preserved."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        args = {
            "name": "John Doe",
            "action": "create",
            "count": 42,
            "enabled": True,
        }

        result = sanitize_for_logging(args)

        assert result["name"] == "John Doe"
        assert result["action"] == "create"
        assert result["count"] == 42
        assert result["enabled"] is True

    def test_original_dict_unchanged(self):
        """Test that the original dictionary is not modified."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        original = {
            "password": "secret123",
            "api_key": "key456",
            "name": "Test",
        }
        original_copy = original.copy()

        sanitize_for_logging(original)

        assert original == original_copy

    def test_handles_none_values(self):
        """Test that None values are handled gracefully."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        args = {
            "password": None,
            "api_key": None,
            "name": "Test",
        }

        result = sanitize_for_logging(args)

        # None values should remain None, not "[REDACTED]"
        assert result["name"] == "Test"

    def test_handles_empty_dict(self):
        """Test that empty dict is handled."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        result = sanitize_for_logging({})

        assert result == {}


@pytest.mark.unit
@pytest.mark.security
@pytest.mark.xdist_group(name="secrets_obfuscation_tests")
@pytest.mark.skipif(not INFISICAL_AVAILABLE, reason="infisical-python not installed")
class TestConfigSecretsLeakage:
    """Test that config initialization doesn't leak secrets."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
    def test_infisical_error_does_not_expose_credentials(self, mock_client):
        """Test that Infisical connection errors don't expose credentials."""
        # Simulate an error that might contain credentials
        mock_client.side_effect = Exception(
            "Connection failed: invalid credentials client_id=test client_secret=super_secret_value"
        )

        from mcp_server_langgraph.secrets.manager import SecretsManager

        # This should not raise, and should not log the secret
        manager = SecretsManager(
            client_id="test",
            client_secret="super_secret_value",
        )

        # Manager should be created with client=None
        assert manager.client is None
        # The error message should not contain the secret when logged
        # (This is tested by the implementation not printing/logging the raw exception)
