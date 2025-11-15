"""Tests for Redis URL encoding with special characters in passwords.

This test module validates proper URL encoding of Redis connection strings,
specifically addressing the production incident where unencoded special characters
in passwords caused ValueError during redis.connection.parse_url().

Related Issue: Staging deployment revision 758b8f744 crash
Root Cause: Password with / and + characters not percent-encoded in Redis URL
"""

import gc

import pytest

from mcp_server_langgraph.core.url_utils import ensure_redis_password_encoded


@pytest.mark.xdist_group(name="testredisurlencoding")
class TestRedisURLEncoding:
    """Test URL encoding for Redis connection strings per RFC 3986."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_password_with_forward_slash_encoded(self):
        """Test password containing '/' is percent-encoded to %2F.

        This is the primary failure case from production where unencoded /
        caused the URL parser to treat the password fragment as a path component.
        """
        url = "redis://:password/with/slashes@localhost:6379/1"
        result = ensure_redis_password_encoded(url)

        # Password should be percent-encoded
        assert "password%2Fwith%2Fslashes" in result
        # Original unencoded password should not appear
        assert "password/with/slashes" not in result
        # Host and port should be unchanged
        assert "@localhost:6379/1" in result

    def test_password_with_plus_sign_encoded(self):
        """Test password containing '+' is percent-encoded to %2B."""
        url = "redis://:pass+word@localhost:6379/1"
        result = ensure_redis_password_encoded(url)

        assert "pass%2Bword" in result
        assert "pass+word@" not in result

    def test_password_with_equals_sign_encoded(self):
        """Test password containing '=' is percent-encoded to %3D."""
        url = "redis://:pass=word@localhost:6379/1"
        result = ensure_redis_password_encoded(url)

        assert "pass%3Dword" in result
        assert "pass=word@" not in result

    def test_base64_like_password_with_multiple_special_chars_encoded(self):
        """Test realistic Base64-like password with multiple special characters.

        This simulates the actual failing password from production:
        Du0PmDvmqDWqDTgfGnmi6/SKyuQydi3z7cPTgEQoE+s=

        The unencoded / caused ValueError: Port could not be cast to integer value
        """
        # Actual production-like password structure
        url = "redis://:Du0PmDvmqDWqDTgfGnmi6/SKyuQydi3z7cPTgEQoE+s=@10.110.1.4:6379/1"
        result = ensure_redis_password_encoded(url)

        # All special characters should be encoded
        assert "%2F" in result  # Forward slash encoded
        assert "%2B" in result  # Plus sign encoded
        assert "%3D" in result  # Equals sign encoded

        # No unencoded special chars should appear in password
        # Extract just the password (after scheme and : separator, before @)
        before_at = result.split("@")[0]  # redis://:password
        password_only = before_at.split(":", 2)[2] if len(before_at.split(":")) > 2 else ""
        assert "/" not in password_only
        assert "+" not in password_only
        assert "=" not in password_only

        # Host and database should be unchanged
        assert "@10.110.1.4:6379/1" in result

    def test_password_without_special_chars_unchanged(self):
        """Test password without special chars passes through unchanged."""
        url = "redis://:simplepassword123@localhost:6379/1"
        result = ensure_redis_password_encoded(url)

        # Should be identical to input
        assert result == url

    def test_url_without_password_unchanged(self):
        """Test URL without password passes through unchanged."""
        url = "redis://localhost:6379/1"
        result = ensure_redis_password_encoded(url)

        assert result == url

    def test_url_with_username_and_password_encoded(self):
        """Test URL with both username and password encodes only password."""
        url = "redis://user:pass/word@localhost:6379/1"
        result = ensure_redis_password_encoded(url)

        # Username should be unchanged
        assert "user:" in result
        # Password should be encoded
        assert "pass%2Fword" in result
        assert "pass/word" not in result

    def test_empty_password_unchanged(self):
        """Test URL with empty password (just colon) unchanged."""
        url = "redis://:@localhost:6379/1"
        result = ensure_redis_password_encoded(url)

        assert result == url

    def test_at_sign_in_password_encoded(self):
        """Test password containing @ is percent-encoded to %40.

        The @ symbol is used as delimiter in URL, so it must be encoded
        if it appears in the password.
        """
        url = "redis://:p@ssword@localhost:6379/1"
        result = ensure_redis_password_encoded(url)

        assert "p%40ssword" in result

    def test_multiple_database_numbers_preserved(self):
        """Test that database number in path is preserved."""
        for db_num in ["0", "1", "15"]:
            url = f"redis://:pass/word@localhost:6379/{db_num}"
            result = ensure_redis_password_encoded(url)

            assert f"/{db_num}" in result
            assert "pass%2Fword" in result

    def test_custom_port_preserved(self):
        """Test that custom Redis port is preserved."""
        url = "redis://:pass+word@redis-host:6380/0"
        result = ensure_redis_password_encoded(url)

        assert ":6380/" in result
        assert "pass%2Bword" in result

    def test_idempotent_encoding(self):
        """Test that encoding same URL twice produces same result.

        This ensures already-encoded passwords are not double-encoded.
        """
        url = "redis://:password/with/slash@localhost:6379/1"

        result1 = ensure_redis_password_encoded(url)
        result2 = ensure_redis_password_encoded(result1)

        # Second encoding should not change the result
        assert result1 == result2
        assert result1.count("%2F") == 2  # Only 2 slashes, not 4

    def test_all_reserved_characters_encoded(self):
        """Test that all RFC 3986 reserved characters are encoded in password.

        Reserved characters that need encoding: : / ? # [ ] @ ! $ & ' ( ) * + , ; =
        """
        # Note: : is the delimiter between username and password, so we exclude it from password
        reserved_chars = "/?#[]@!$&'()*+,;="
        password = f"test{reserved_chars}pass"
        url = f"redis://:{password}@localhost:6379/1"

        result = ensure_redis_password_encoded(url)

        # None of the reserved characters should appear unencoded in password portion
        password_portion = result.split("@")[0].split(":", 2)[2]  # Extract password part

        for char in reserved_chars:
            assert char not in password_portion, f"Character '{char}' should be encoded but found in: {password_portion}"

        # Should contain percent-encoded values
        assert "%" in password_portion
