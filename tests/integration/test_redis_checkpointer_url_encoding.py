"""Integration tests for Redis checkpointer with URL-encoded passwords.

This test module prevents regression of the production incident where unencoded
special characters in Redis passwords caused pod crashes (staging revision 758b8f744).

Tests validate:
1. Redis checkpointer initialization with encoded passwords
2. End-to-end URL encoding flow from config → agent → Redis connection
3. Defense-in-depth safeguards prevent malformed URLs
"""

import gc
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_langgraph.core.config import Settings
from mcp_server_langgraph.core.url_utils import ensure_redis_password_encoded


@pytest.mark.xdist_group(name="integration_redis_checkpointer_url_encoding_tests")
class TestRedisCheckpointerURLEncoding:
    """Integration tests for Redis checkpointer URL encoding safeguards."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.parametrize(
        "password,expected_encoded",
        [
            # Production incident password (actual case from staging-758b8f744)
            # gitleaks:allow - Test fixture from documented incident
            ("Du0PmDvmqDWqDTgfGnmi6/SKyuQydi3z7cPTgfGnmi6+s=", "Du0PmDvmqDWqDTgfGnmi6%2FSKyuQydi3z7cPTgfGnmi6%2Bs%3D"),
            # Common Base64 patterns
            ("abc123+def456=", "abc123%2Bdef456%3D"),
            ("test/path+value=end", "test%2Fpath%2Bvalue%3Dend"),
            # Edge cases
            ("p@ssw0rd", "p%40ssw0rd"),
            ("pass word", "pass%20word"),
            # Multiple special characters
            ("a/b+c=d@e!f", "a%2Fb%2Bc%3Dd%40e%21f"),
        ],
    )
    def test_ensure_redis_password_encoded_parametrized(self, password: str, expected_encoded: str):
        """Test password encoding with various special character combinations."""
        url = f"redis://:{password}@localhost:6379/1"
        result = ensure_redis_password_encoded(url)

        # Verify encoded password appears in result
        assert expected_encoded in result, f"Expected {expected_encoded} in {result}"

        # Verify original password does NOT appear (was encoded)
        password_portion = result.split("@")[0].split(":", 2)[2]
        assert password not in password_portion

    def test_checkpointer_factory_applies_url_encoding(self):
        """Test that _create_checkpointer applies URL encoding before Redis connection."""
        from mcp_server_langgraph.core.agent import _create_checkpointer

        # Create settings with unencoded password containing special chars
        test_settings = Settings.model_construct(
            checkpoint_backend="redis",
            checkpoint_redis_url="redis://:test/password+123=@localhost:6379/1",
        )

        with patch("mcp_server_langgraph.core.agent.settings", test_settings):
            with patch("mcp_server_langgraph.core.agent.RedisSaver") as mock_redis_saver:
                # Mock the from_conn_string context manager
                mock_context = MagicMock()
                mock_redis_saver.from_conn_string.return_value = mock_context

                _create_checkpointer()

                # Verify RedisSaver was called with ENCODED URL
                call_args = mock_redis_saver.from_conn_string.call_args
                redis_url_arg = call_args.kwargs.get("redis_url")

                assert redis_url_arg is not None, "redis_url parameter not passed"
                assert "test%2Fpassword%2B123%3D" in redis_url_arg, f"Password not encoded in {redis_url_arg}"
                assert "test/password+123=" not in redis_url_arg, f"Unencoded password found in {redis_url_arg}"

    def test_checkpointer_factory_handles_already_encoded_urls(self):
        """Test that _create_checkpointer is idempotent for already-encoded URLs."""
        from mcp_server_langgraph.core.agent import _create_checkpointer

        # Pre-encoded URL
        test_settings = Settings.model_construct(
            checkpoint_backend="redis",
            checkpoint_redis_url="redis://:test%2Fpassword%2B123%3D@localhost:6379/1",
        )

        with patch("mcp_server_langgraph.core.agent.settings", test_settings):
            with patch("mcp_server_langgraph.core.agent.RedisSaver") as mock_redis_saver:
                mock_context = MagicMock()
                mock_redis_saver.from_conn_string.return_value = mock_context

                _create_checkpointer()

                # Verify URL was not double-encoded
                call_args = mock_redis_saver.from_conn_string.call_args
                redis_url_arg = call_args.kwargs.get("redis_url")

                # Should have exactly one set of encoded chars (not double-encoded)
                assert redis_url_arg.count("%2F") == 1, "Password double-encoded (/ → %2F → %252F)"
                assert redis_url_arg.count("%2B") == 1, "Password double-encoded (+ → %2B → %252B)"
                assert redis_url_arg.count("%3D") == 1, "Password double-encoded (= → %3D → %253D)"

    def test_memory_checkpointer_ignores_url_encoding(self):
        """Test that memory checkpointer doesn't attempt URL encoding."""
        from langgraph.checkpoint.memory import MemorySaver

        from mcp_server_langgraph.core.agent import _create_checkpointer

        test_settings = Settings.model_construct(
            checkpoint_backend="memory",
        )

        with patch("mcp_server_langgraph.core.agent.settings", test_settings):
            checkpointer = _create_checkpointer()

            # Should return MemorySaver without any Redis operations
            assert isinstance(checkpointer, MemorySaver)

    @pytest.mark.parametrize(
        "invalid_url",
        [
            "redis://localhost:6379/1",  # No password (should pass through)
            "redis://:@localhost:6379/1",  # Empty password (should pass through)
            "http://not-redis:8080",  # Wrong scheme (should pass through)
        ],
    )
    def test_url_encoding_handles_edge_cases_safely(self, invalid_url: str):
        """Test that URL encoding handles edge cases without crashing."""
        result = ensure_redis_password_encoded(invalid_url)
        # Should return unchanged for non-password URLs
        assert result == invalid_url

    def test_production_incident_password_encoded_correctly(self):
        """Test exact password from production incident (staging-758b8f744).

        This test captures the EXACT failure case:
        - Password: Du0PmDvmqDWqDTgfGnmi6/SKyuQydi3z7cPTgfGnmi6+s=
        - Error: ValueError: Port could not be cast to integer value as 'Du0PmDvmqDWqDTgfGnmi6'
        - Cause: Unencoded / treated as path separator
        """
        # Exact production password that caused the crash
        # gitleaks:allow - This is a test fixture from a documented production incident, not a real secret
        production_password = "Du0PmDvmqDWqDTgfGnmi6/SKyuQydi3z7cPTgfGnmi6+s="

        # Exact production URL structure
        url = f"redis://:{production_password}@10.110.1.4:6379/1"

        # Apply encoding
        result = ensure_redis_password_encoded(url)

        # Verify all special characters are encoded
        assert "%2F" in result, "Forward slash (/) not encoded"
        assert "%2B" in result, "Plus sign (+) not encoded"
        assert "%3D" in result, "Equals sign (=) not encoded"

        # Verify host and database preserved
        assert "@10.110.1.4:6379/1" in result

        # Verify no unencoded special chars in password portion
        password_portion = result.split("@")[0].split(":", 2)[2]
        assert "/" not in password_portion
        assert "+" not in password_portion
        # Note: = can appear in %3D encoding
        assert production_password not in result

    def test_external_secrets_template_simulation(self):
        """Simulate External Secrets template with urlquery filter.

        This test validates that the Kubernetes External Secrets pattern
        (with | urlquery filter) produces correctly encoded URLs.
        """
        # Simulate the template variables
        # gitleaks:allow - This is a test fixture from a documented production incident, not a real secret
        redis_password = "Du0PmDvmqDWqDTgfGnmi6/SKyuQydi3z7cPTgfGnmi6+s="
        redis_host = "10.110.1.4"

        # Simulate | urlquery filter (Python's quote function)
        from urllib.parse import quote

        encoded_password = quote(redis_password, safe="")

        # Construct URL as External Secrets template would
        template_url = f"redis://:{encoded_password}@{redis_host}:6379/1"

        # Verify template produces valid URL
        assert "%2F" in template_url
        assert "%2B" in template_url
        assert "%3D" in template_url

        # Verify application-level encoding is idempotent with template encoding
        app_encoded_url = ensure_redis_password_encoded(template_url)
        assert app_encoded_url == template_url, "Application encoding should be idempotent with template encoding"


@pytest.mark.xdist_group(name="integration_redis_checkpointer_url_encoding_tests")
class TestRedisCheckpointerDefenseInDepth:
    """Tests for defense-in-depth URL encoding safeguards."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_three_layer_protection(self):
        """Validate three-layer protection against URL encoding issues.

        Layer 1: External Secrets template (| urlquery filter)
        Layer 2: Application-level encoding (ensure_redis_password_encoded)
        Layer 3: Test coverage (this test suite)
        """
        from urllib.parse import quote

        password = "test/pass+word="

        # Layer 1: Template encoding (External Secrets)
        template_encoded = f"redis://:{quote(password, safe='')}@host:6379/1"

        # Layer 2: Application encoding (defense-in-depth)
        app_encoded = ensure_redis_password_encoded(template_encoded)

        # Both layers should produce same result (idempotent)
        assert template_encoded == app_encoded

        # Layer 3: This test validates correctness
        assert "%2F" in app_encoded
        assert "%2B" in app_encoded
        assert "%3D" in app_encoded

    def test_malformed_url_from_config_gets_fixed(self):
        """Test that malformed URLs from config are automatically fixed."""
        # Simulate misconfiguration (forgot to encode password)
        malformed_url = "redis://:bad/password+123=@host:6379/1"

        # Application-level defense should fix it
        fixed_url = ensure_redis_password_encoded(malformed_url)

        assert "bad%2Fpassword%2B123%3D" in fixed_url
        assert "bad/password+123=" not in fixed_url

    def test_url_encoding_preserves_connection_semantics(self):
        """Test that encoding preserves Redis connection semantics."""
        original_url = "redis://:mypassword@localhost:6379/1"
        encoded_url = ensure_redis_password_encoded(original_url)

        # Parse both URLs
        import re

        def parse_redis_url(url):
            match = re.match(r"redis://:(.*?)@(.*?):(.*?)/(.*)", url)
            if match:
                return {
                    "password": match.group(1),
                    "host": match.group(2),
                    "port": match.group(3),
                    "db": match.group(4),
                }
            return None

        original_parts = parse_redis_url(original_url)
        encoded_parts = parse_redis_url(encoded_url)

        # Host, port, and database should be unchanged
        assert original_parts["host"] == encoded_parts["host"]
        assert original_parts["port"] == encoded_parts["port"]
        assert original_parts["db"] == encoded_parts["db"]

        # Password should be the same (just encoded)
        from urllib.parse import unquote

        assert original_parts["password"] == unquote(encoded_parts["password"])


@pytest.mark.xdist_group(name="integration_redis_checkpointer_url_encoding_tests")
class TestRegressionPrevention:
    """Regression tests to prevent future incidents of this class."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_redis_connection_with_special_chars_does_not_crash(self):
        """Test that Redis connections with special char passwords don't crash.

        This is the ultimate regression test - simulating the exact failure
        from production and ensuring it doesn't occur.
        """
        from mcp_server_langgraph.core.agent import _create_checkpointer

        # Use exact password that caused production crash
        test_settings = Settings.model_construct(
            checkpoint_backend="redis",
            checkpoint_redis_url="redis://:Du0PmDvmqDWqDTgfGnmi6/SKyuQydi3z7cPTgfGnmi6+s=@10.110.1.4:6379/1",
        )

        with patch("mcp_server_langgraph.core.agent.settings", test_settings):
            with patch("mcp_server_langgraph.core.agent.RedisSaver") as mock_redis_saver:
                mock_context = MagicMock()
                mock_redis_saver.from_conn_string.return_value = mock_context

                # This should NOT raise ValueError about port casting
                try:
                    _create_checkpointer()
                    success = True
                except ValueError as e:
                    if "Port could not be cast to integer" in str(e):
                        success = False
                        pytest.fail(f"Production incident regression detected: {e}")
                    raise

                assert success, "Checkpointer creation should succeed with encoded URL"

    def test_all_rfc3986_reserved_chars_handled(self):
        """Test that ALL RFC 3986 reserved characters are properly encoded."""
        # RFC 3986 gen-delims: : / ? # [ ] @
        # RFC 3986 sub-delims: ! $ & ' ( ) * + , ; =
        reserved_chars = ":/?#[]@!$&'()*+,;="

        # Create password with all reserved chars (exclude : as it's the delimiter)
        password = "test" + reserved_chars.replace(":", "") + "end"
        url = f"redis://:{password}@host:6379/1"

        result = ensure_redis_password_encoded(url)

        # Extract password portion
        password_portion = result.split("@")[0].split(":", 2)[2]

        # Verify none of the reserved chars appear unencoded (except in %XX sequences)
        # Remove all %XX sequences first
        import re

        without_encoding = re.sub(r"%[0-9A-F]{2}", "", password_portion)

        for char in reserved_chars.replace(":", ""):
            assert char not in without_encoding, f"Reserved character '{char}' found unencoded in password"
