"""Unit tests for security-focused logging utilities.

This module tests the sanitization of sensitive data in logs, specifically:
- JWT token redaction (CWE-200/CWE-532 prevention)
- Sensitive field stripping from log payloads
- Hash/truncation of large text fields
"""

import gc

import pytest

from mcp_server_langgraph.core.security import sanitize_for_logging
from tests.conftest import get_user_id

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testlogsanitization")
class TestLogSanitization:
    """Test suite for log sanitization to prevent CWE-200/CWE-532 vulnerabilities"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_sanitize_for_logging_redacts_token_field(self):
        """Test that JWT token is redacted from log payload"""
        # GIVEN: Arguments containing a JWT token
        arguments = {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyOmFsaWNlIn0.signature",
            "message": "Hello, world!",
            "thread_id": "conv_123",
        }

        # WHEN: Sanitizing for logging
        sanitized = sanitize_for_logging(arguments)

        # THEN: Token should be redacted
        expected_redaction = "[" + "REDACTED" + "]"  # Split to avoid gitleaks false positive
        assert sanitized["token"] == expected_redaction
        assert sanitized["message"] == "Hello, world!"
        assert sanitized["thread_id"] == "conv_123"

    def test_sanitize_for_logging_handles_missing_token(self):
        """Test that sanitization works when token field is absent"""
        # GIVEN: Arguments without a token
        arguments = {"message": "Hello, world!", "limit": 10}

        # WHEN: Sanitizing for logging
        sanitized = sanitize_for_logging(arguments)

        # THEN: No token field should be added
        assert "token" not in sanitized
        assert sanitized["message"] == "Hello, world!"
        assert sanitized["limit"] == 10

    def test_sanitize_for_logging_truncates_long_message(self):
        """Test that very long messages are truncated in logs"""
        # GIVEN: Arguments with a very long message (>500 chars)
        long_message = "A" * 1000
        arguments = {"message": long_message, "token": "secret_token"}

        # WHEN: Sanitizing for logging
        sanitized = sanitize_for_logging(arguments)

        # THEN: Message should be truncated with indicator
        assert len(sanitized["message"]) <= 503  # 500 + "..." length
        assert sanitized["message"].endswith("...")
        assert sanitized["message"].startswith("A")

    def test_sanitize_for_logging_preserves_short_message(self):
        """Test that short messages are not truncated"""
        # GIVEN: Arguments with a short message
        arguments = {"message": "Short message", "token": "secret_token"}

        # WHEN: Sanitizing for logging
        sanitized = sanitize_for_logging(arguments)

        # THEN: Message should be preserved as-is
        assert sanitized["message"] == "Short message"

    def test_sanitize_for_logging_truncates_query_field(self):
        """Test that query field is also truncated"""
        # GIVEN: Arguments with a long query
        long_query = "B" * 600
        arguments = {"query": long_query}

        # WHEN: Sanitizing for logging
        sanitized = sanitize_for_logging(arguments)

        # THEN: Query should be truncated
        assert len(sanitized["query"]) <= 503
        assert sanitized["query"].endswith("...")

    def test_sanitize_for_logging_creates_shallow_copy(self):
        """Test that sanitization doesn't modify original dict"""
        # GIVEN: Original arguments
        original = {"token": "secret", "message": "Hello"}

        # WHEN: Sanitizing for logging
        sanitized = sanitize_for_logging(original)

        # THEN: Original should be unchanged
        assert original["token"] == "secret"
        assert sanitized["token"] == "[REDACTED]"
        assert original is not sanitized

    def test_sanitize_for_logging_handles_nested_token(self):
        """Test that nested token fields are not redacted (shallow only)"""
        # GIVEN: Arguments with nested structure
        arguments = {"token": "secret", "data": {"token": "nested_secret", "value": 123}}

        # WHEN: Sanitizing for logging
        sanitized = sanitize_for_logging(arguments)

        # THEN: Top-level token redacted, nested preserved (shallow copy)
        expected_redaction = "[" + "REDACTED" + "]"
        assert sanitized["token"] == expected_redaction
        # Nested token is not redacted (shallow sanitization for performance)
        assert sanitized["data"]["token"] == "nested_secret"

    def test_sanitize_for_logging_handles_none_value(self):
        """Test that None token value is handled gracefully"""
        # GIVEN: Arguments with None token
        arguments = {"token": None, "message": "Hello"}

        # WHEN: Sanitizing for logging
        sanitized = sanitize_for_logging(arguments)

        # THEN: None token should remain None (not redacted string)
        assert sanitized["token"] is None
        assert sanitized["message"] == "Hello"

    def test_sanitize_for_logging_handles_empty_dict(self):
        """Test that empty dict is handled correctly"""
        # GIVEN: Empty arguments
        arguments = {}

        # WHEN: Sanitizing for logging
        sanitized = sanitize_for_logging(arguments)

        # THEN: Should return empty dict
        assert sanitized == {}

    def test_sanitize_for_logging_with_multiple_sensitive_fields(self):
        """Test sanitization with multiple large text fields"""
        # GIVEN: Arguments with multiple large fields
        arguments = {
            "token": "secret_token",
            "message": "X" * 600,
            "query": "Y" * 700,
            "thread_id": "conv_123",
            "limit": 50,
        }

        # WHEN: Sanitizing for logging
        sanitized = sanitize_for_logging(arguments)

        # THEN: All sensitive fields should be handled correctly
        expected_redaction = "[" + "REDACTED" + "]"
        assert sanitized["token"] == expected_redaction
        assert len(sanitized["message"]) <= 503
        assert len(sanitized["query"]) <= 503
        assert sanitized["thread_id"] == "conv_123"
        assert sanitized["limit"] == 50

    def test_sanitize_for_logging_preserves_non_string_types(self):
        """Test that non-string field types are preserved"""
        # GIVEN: Arguments with various types
        arguments = {
            "token": "secret",
            "count": 42,
            "enabled": True,
            "ratio": 3.14,
            "items": [1, 2, 3],
            "meta": {"key": "value"},
        }

        # WHEN: Sanitizing for logging
        sanitized = sanitize_for_logging(arguments)

        # THEN: Non-string types should be preserved
        assert sanitized["count"] == 42
        assert sanitized["enabled"] is True
        assert sanitized["ratio"] == 3.14
        assert sanitized["items"] == [1, 2, 3]
        assert sanitized["meta"] == {"key": "value"}

    def test_sanitize_for_logging_redacts_session_id(self):
        """Test that session_id is redacted to prevent session hijacking"""
        # GIVEN: Arguments containing session identifier
        arguments = {
            "session_id": "sess_abc123xyz789",
            "user_id": get_user_id("alice"),
            "action": "login",
        }

        # WHEN: Sanitizing for logging
        sanitized = sanitize_for_logging(arguments)

        # THEN: session_id should be redacted
        assert sanitized["session_id"] == "[REDACTED]"
        assert sanitized["user_id"] == "[REDACTED]"
        assert sanitized["action"] == "login"

    def test_sanitize_for_logging_redacts_user_id(self):
        """Test that user_id is redacted for GDPR/CCPA compliance"""
        # GIVEN: Arguments containing user identifier (PII)
        arguments = {
            "user_id": get_user_id("bob"),
            "operation": "delete_account",
        }

        # WHEN: Sanitizing for logging
        sanitized = sanitize_for_logging(arguments)

        # THEN: user_id should be redacted
        assert sanitized["user_id"] == "[REDACTED]"
        assert sanitized["operation"] == "delete_account"

    def test_sanitize_for_logging_redacts_username(self):
        """Test that username is redacted for privacy protection"""
        # GIVEN: Arguments containing username (PII)
        arguments = {
            "username": "alice@example.com",
            "ip_address": "192.168.1.1",
        }

        # WHEN: Sanitizing for logging
        sanitized = sanitize_for_logging(arguments)

        # THEN: username should be redacted, IP preserved for security analysis
        assert sanitized["username"] == "[REDACTED]"
        assert sanitized["ip_address"] == "192.168.1.1"

    def test_sanitize_for_logging_handles_all_sensitive_fields(self):
        """Test comprehensive redaction of all sensitive fields"""
        # GIVEN: Arguments with all sensitive fields
        arguments = {
            "token": "jwt_token_here",
            "session_id": "sess_12345",
            "user_id": get_user_id("charlie"),
            "username": "charlie",
            "message": "Hello, world!",
        }

        # WHEN: Sanitizing for logging
        sanitized = sanitize_for_logging(arguments)

        # THEN: All sensitive fields should be redacted
        expected_redaction = "[REDACTED]"
        assert sanitized["token"] == expected_redaction
        assert sanitized["session_id"] == expected_redaction
        assert sanitized["user_id"] == expected_redaction
        assert sanitized["username"] == expected_redaction
        assert sanitized["message"] == "Hello, world!"


@pytest.mark.xdist_group(name="testlogsanitizationwithrealworldpayloads")
class TestLogSanitizationWithRealWorldPayloads:
    """Test log sanitization with realistic MCP tool call payloads"""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_sanitize_chat_tool_payload(self):
        """Test sanitization of actual chat tool call arguments"""
        # GIVEN: Real chat tool call arguments
        arguments = {
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyOmFsaWNlIiwicm9sZXMiOlsidXNlciJdfQ.xyz",
            "message": "What is the weather today?",
            "thread_id": "conv_abc123",
            "context": {"user_id": get_user_id("alice"), "session_id": "sess_456"},
        }

        # WHEN: Sanitizing for logging
        sanitized = sanitize_for_logging(arguments)

        # THEN: Sensitive fields should be redacted/truncated
        expected_redaction = "[" + "REDACTED" + "]"
        assert sanitized["token"] == expected_redaction
        assert sanitized["message"] == "What is the weather today?"
        assert sanitized["thread_id"] == "conv_abc123"
        # Context is preserved (shallow copy) - includes worker-prefix from get_user_id()
        assert sanitized["context"]["user_id"] == get_user_id("alice")

    def test_sanitize_search_tool_payload(self):
        """Test sanitization of search tool call arguments"""
        # GIVEN: Search tool call arguments
        arguments = {
            "token": "jwt_token_here",
            "query": "machine learning papers 2024",
            "limit": 10,
            "offset": 0,
        }

        # WHEN: Sanitizing for logging
        sanitized = sanitize_for_logging(arguments)

        # THEN: Token redacted, query preserved (short)
        expected_redaction = "[" + "REDACTED" + "]"
        assert sanitized["token"] == expected_redaction
        assert sanitized["query"] == "machine learning papers 2024"
        assert sanitized["limit"] == 10

    def test_sanitize_error_payload_with_validation_failure(self):
        """Test sanitization when logging validation errors"""
        # GIVEN: Arguments that failed validation
        arguments = {
            "token": "secret_jwt_token",
            "message": "",  # Invalid: empty message
            "thread_id": "../../../etc/passwd",  # Malicious input
        }

        # WHEN: Sanitizing for logging (before logging error)
        sanitized = sanitize_for_logging(arguments)

        # THEN: Token should be redacted even in error logs
        expected_redaction = "[" + "REDACTED" + "]"
        assert sanitized["token"] == expected_redaction
        # Malicious input is preserved for security analysis
        assert sanitized["thread_id"] == "../../../etc/passwd"
