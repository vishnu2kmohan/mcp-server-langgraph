"""
Unit tests for core/url_utils.py.

Tests Redis URL password encoding for RFC 3986 compliance.
Follows TDD principles and memory safety patterns for pytest-xdist.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="url_utils")
class TestEnsureRedisPasswordEncoded:
    """Test ensure_redis_password_encoded function."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_encodes_forward_slash_in_password(self):
        """Test that forward slash in password is encoded."""
        from mcp_server_langgraph.core.url_utils import ensure_redis_password_encoded

        url = "redis://:pass/word@localhost:6379/1"
        result = ensure_redis_password_encoded(url)

        assert "%2F" in result
        assert "pass%2Fword" in result

    @pytest.mark.unit
    def test_encodes_plus_sign_in_password(self):
        """Test that plus sign in password is encoded."""
        from mcp_server_langgraph.core.url_utils import ensure_redis_password_encoded

        url = "redis://:pass+word@localhost:6379/0"
        result = ensure_redis_password_encoded(url)

        assert "%2B" in result
        assert "pass%2Bword" in result

    @pytest.mark.unit
    def test_encodes_equals_sign_in_password(self):
        """Test that equals sign in password is encoded."""
        from mcp_server_langgraph.core.url_utils import ensure_redis_password_encoded

        url = "redis://:pass=word@localhost:6379/0"
        result = ensure_redis_password_encoded(url)

        assert "%3D" in result

    @pytest.mark.unit
    def test_encodes_at_sign_in_password(self):
        """Test that @ sign in password is encoded."""
        from mcp_server_langgraph.core.url_utils import ensure_redis_password_encoded

        url = "redis://:pass@word@localhost:6379/0"
        result = ensure_redis_password_encoded(url)

        # The last @ should remain as delimiter
        assert result.count("@") == 1
        assert "%40" in result

    @pytest.mark.unit
    def test_encodes_complex_password_with_multiple_special_chars(self):
        """Test encoding password with multiple special characters."""
        from mcp_server_langgraph.core.url_utils import ensure_redis_password_encoded

        # Real-world example from production incident
        url = "redis://:Du0PmDvmqDWqDTgfGnmi6/SKyuQydi3z7cPTgEQoE+s=@redis-host:6379/0"
        result = ensure_redis_password_encoded(url)

        # Should encode / and + and =
        assert "%2F" in result
        assert "%2B" in result
        assert "%3D" in result
        # Host should remain
        assert "@redis-host:6379/0" in result

    @pytest.mark.unit
    def test_returns_unchanged_url_without_password(self):
        """Test that URLs without password are returned unchanged."""
        from mcp_server_langgraph.core.url_utils import ensure_redis_password_encoded

        url = "redis://localhost:6379/1"
        result = ensure_redis_password_encoded(url)

        assert result == url

    @pytest.mark.unit
    def test_returns_unchanged_url_without_auth(self):
        """Test that URLs without @ are returned unchanged."""
        from mcp_server_langgraph.core.url_utils import ensure_redis_password_encoded

        url = "redis://localhost:6379/0"
        result = ensure_redis_password_encoded(url)

        assert result == url

    @pytest.mark.unit
    def test_returns_unchanged_url_with_non_redis_scheme(self):
        """Test that non-redis URLs are returned unchanged."""
        from mcp_server_langgraph.core.url_utils import ensure_redis_password_encoded

        url = "http://user:pass@example.com/path"
        result = ensure_redis_password_encoded(url)

        assert result == url

    @pytest.mark.unit
    def test_preserves_username_in_url(self):
        """Test that username is preserved in the URL."""
        from mcp_server_langgraph.core.url_utils import ensure_redis_password_encoded

        url = "redis://myuser:mypassword@localhost:6379/0"
        result = ensure_redis_password_encoded(url)

        assert result.startswith("redis://myuser:")
        assert "@localhost:6379/0" in result

    @pytest.mark.unit
    def test_handles_empty_password(self):
        """Test that empty password is handled correctly."""
        from mcp_server_langgraph.core.url_utils import ensure_redis_password_encoded

        url = "redis://:@localhost:6379/0"
        result = ensure_redis_password_encoded(url)

        # Empty password should return original
        assert result == url

    @pytest.mark.unit
    def test_idempotent_already_encoded_password(self):
        """Test that already-encoded passwords are not double-encoded."""
        from mcp_server_langgraph.core.url_utils import ensure_redis_password_encoded

        # Password already encoded
        url = "redis://:pass%2Fword@localhost:6379/0"
        result = ensure_redis_password_encoded(url)

        # Should not double-encode (%2F should not become %252F)
        assert "%252F" not in result
        assert "pass%2Fword" in result

    @pytest.mark.unit
    def test_handles_password_with_colon(self):
        """Test that colons in password are handled correctly."""
        from mcp_server_langgraph.core.url_utils import ensure_redis_password_encoded

        url = "redis://:pass:word:123@localhost:6379/0"
        result = ensure_redis_password_encoded(url)

        # Colons in password should be encoded
        assert "%3A" in result
        assert "@localhost:6379/0" in result

    @pytest.mark.unit
    def test_preserves_database_number(self):
        """Test that database number in path is preserved."""
        from mcp_server_langgraph.core.url_utils import ensure_redis_password_encoded

        url = "redis://:simplepass@localhost:6379/5"
        result = ensure_redis_password_encoded(url)

        assert result.endswith("/5")

    @pytest.mark.unit
    def test_preserves_port_number(self):
        """Test that port number is preserved."""
        from mcp_server_langgraph.core.url_utils import ensure_redis_password_encoded

        url = "redis://:simplepass@localhost:6380/0"
        result = ensure_redis_password_encoded(url)

        assert ":6380/" in result
