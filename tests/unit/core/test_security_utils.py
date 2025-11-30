"""
Unit tests for core/security.py utility functions.

Tests sanitization functions for log safety and HTTP header protection.
Follows TDD principles and memory safety patterns for pytest-xdist.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="security_utils")
class TestSanitizeForLogging:
    """Test sanitize_for_logging function."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_sanitize_redacts_token_field(self):
        """Test that token field is redacted."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        args = {"token": "secret-jwt-token-12345", "message": "hello"}

        result = sanitize_for_logging(args)

        assert result["token"] == "[REDACTED]"
        assert result["message"] == "hello"

    @pytest.mark.unit
    def test_sanitize_redacts_session_id_field(self):
        """Test that session_id field is redacted."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        args = {"session_id": "sess_abc123", "data": "value"}

        result = sanitize_for_logging(args)

        assert result["session_id"] == "[REDACTED]"
        assert result["data"] == "value"

    @pytest.mark.unit
    def test_sanitize_redacts_user_id_field(self):
        """Test that user_id field is redacted."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        args = {"user_id": "user:alice", "action": "login"}

        result = sanitize_for_logging(args)

        assert result["user_id"] == "[REDACTED]"
        assert result["action"] == "login"

    @pytest.mark.unit
    def test_sanitize_redacts_username_field(self):
        """Test that username field is redacted."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        args = {"username": "alice", "role": "admin"}

        result = sanitize_for_logging(args)

        assert result["username"] == "[REDACTED]"
        assert result["role"] == "admin"

    @pytest.mark.unit
    def test_sanitize_truncates_long_message(self):
        """Test that long message fields are truncated."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        long_message = "x" * 1000
        args = {"message": long_message}

        result = sanitize_for_logging(args, max_length=100)

        assert len(result["message"]) == 103  # 100 chars + "..."
        assert result["message"].endswith("...")

    @pytest.mark.unit
    def test_sanitize_truncates_long_query(self):
        """Test that long query fields are truncated."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        long_query = "search " * 200
        args = {"query": long_query}

        result = sanitize_for_logging(args, max_length=50)

        assert len(result["query"]) == 53  # 50 chars + "..."
        assert result["query"].endswith("...")

    @pytest.mark.unit
    def test_sanitize_preserves_short_message(self):
        """Test that short messages are not truncated."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        args = {"message": "short message"}

        result = sanitize_for_logging(args)

        assert result["message"] == "short message"

    @pytest.mark.unit
    def test_sanitize_does_not_modify_original(self):
        """Test that original dictionary is not modified."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        original = {"token": "secret", "user_id": "alice"}

        sanitize_for_logging(original)

        assert original["token"] == "secret"
        assert original["user_id"] == "alice"

    @pytest.mark.unit
    def test_sanitize_handles_none_values(self):
        """Test that None values are not redacted."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        args = {"token": None, "user_id": None}

        result = sanitize_for_logging(args)

        # None values should not be changed
        assert result["token"] is None
        assert result["user_id"] is None

    @pytest.mark.unit
    def test_sanitize_handles_empty_dict(self):
        """Test that empty dict returns empty dict."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        result = sanitize_for_logging({})

        assert result == {}

    @pytest.mark.unit
    def test_sanitize_preserves_other_fields(self):
        """Test that non-sensitive fields are preserved."""
        from mcp_server_langgraph.core.security import sanitize_for_logging

        args = {
            "thread_id": "conv-123",
            "response_format": "json",
            "limit": 10,
            "nested": {"key": "value"},
        }

        result = sanitize_for_logging(args)

        assert result["thread_id"] == "conv-123"
        assert result["response_format"] == "json"
        assert result["limit"] == 10
        assert result["nested"] == {"key": "value"}


@pytest.mark.xdist_group(name="security_utils")
class TestSanitizeHeaderValue:
    """Test sanitize_header_value function."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.unit
    def test_sanitize_removes_carriage_return(self):
        """Test that carriage return is removed."""
        from mcp_server_langgraph.core.security import sanitize_header_value

        value = "alice\rX-Evil: injected"

        result = sanitize_header_value(value)

        assert "\r" not in result
        assert result == "aliceX-Evil: injected"

    @pytest.mark.unit
    def test_sanitize_removes_line_feed(self):
        """Test that line feed is removed."""
        from mcp_server_langgraph.core.security import sanitize_header_value

        value = "alice\nX-Evil: injected"

        result = sanitize_header_value(value)

        assert "\n" not in result
        assert result == "aliceX-Evil: injected"

    @pytest.mark.unit
    def test_sanitize_removes_crlf_sequence(self):
        """Test that CRLF sequence is removed (HTTP Response Splitting)."""
        from mcp_server_langgraph.core.security import sanitize_header_value

        value = "alice\r\nSet-Cookie: session=hacked"

        result = sanitize_header_value(value)

        assert "\r\n" not in result
        assert "Set-Cookie" in result  # Characters preserved, just CRLF removed

    @pytest.mark.unit
    def test_sanitize_removes_null_bytes(self):
        """Test that null bytes are removed."""
        from mcp_server_langgraph.core.security import sanitize_header_value

        value = "alice\x00bob"

        result = sanitize_header_value(value)

        assert "\x00" not in result
        assert result == "alicebob"

    @pytest.mark.unit
    def test_sanitize_replaces_tabs_with_spaces(self):
        """Test that tabs are replaced with spaces."""
        from mcp_server_langgraph.core.security import sanitize_header_value

        value = "alice\tbob"

        result = sanitize_header_value(value)

        assert "\t" not in result
        assert result == "alice bob"

    @pytest.mark.unit
    def test_sanitize_removes_path_traversal_forward(self):
        """Test that forward path traversal is removed."""
        from mcp_server_langgraph.core.security import sanitize_header_value

        value = "../../etc/passwd"

        result = sanitize_header_value(value)

        assert "../" not in result

    @pytest.mark.unit
    def test_sanitize_removes_path_traversal_backward(self):
        """Test that backward path traversal is removed."""
        from mcp_server_langgraph.core.security import sanitize_header_value

        value = "..\\..\\windows\\system32"

        result = sanitize_header_value(value)

        assert "..\\" not in result

    @pytest.mark.unit
    def test_sanitize_enforces_max_length(self):
        """Test that value is truncated to max_length."""
        from mcp_server_langgraph.core.security import sanitize_header_value

        value = "a" * 200

        result = sanitize_header_value(value, max_length=50)

        assert len(result) == 50

    @pytest.mark.unit
    def test_sanitize_strips_whitespace(self):
        """Test that leading/trailing whitespace is stripped."""
        from mcp_server_langgraph.core.security import sanitize_header_value

        value = "  alice  "

        result = sanitize_header_value(value)

        assert result == "alice"

    @pytest.mark.unit
    def test_sanitize_handles_empty_string(self):
        """Test that empty string returns empty string."""
        from mcp_server_langgraph.core.security import sanitize_header_value

        result = sanitize_header_value("")

        assert result == ""

    @pytest.mark.unit
    def test_sanitize_handles_none_like_value(self):
        """Test that falsy empty string returns empty string."""
        from mcp_server_langgraph.core.security import sanitize_header_value

        result = sanitize_header_value("")

        assert result == ""

    @pytest.mark.unit
    def test_sanitize_preserves_safe_characters(self):
        """Test that safe characters are preserved."""
        from mcp_server_langgraph.core.security import sanitize_header_value

        value = "alice_bob-123.txt"

        result = sanitize_header_value(value)

        assert result == "alice_bob-123.txt"

    @pytest.mark.unit
    def test_sanitize_handles_unicode_characters(self):
        """Test that unicode characters are preserved."""
        from mcp_server_langgraph.core.security import sanitize_header_value

        value = "用户名_测试"

        result = sanitize_header_value(value)

        assert result == "用户名_测试"
