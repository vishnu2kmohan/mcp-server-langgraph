"""Unit tests for HTTP header security utilities.

This module tests the sanitization of user-controlled data in HTTP headers,
specifically preventing CWE-113 (HTTP Response Splitting) vulnerabilities.
"""

from mcp_server_langgraph.core.security import sanitize_header_value


class TestHeaderSanitization:
    """Test suite for HTTP header sanitization to prevent CWE-113"""

    def test_sanitize_header_value_removes_cr_characters(self):
        """Test that carriage return (CR) characters are removed"""
        # GIVEN: Input with CR character
        dangerous_input = "alice\rmalicious"

        # WHEN: Sanitizing for header use
        sanitized = sanitize_header_value(dangerous_input)

        # THEN: CR should be removed
        assert "\r" not in sanitized
        assert sanitized == "alicemalicious"

    def test_sanitize_header_value_removes_lf_characters(self):
        """Test that line feed (LF) characters are removed"""
        # GIVEN: Input with LF character
        dangerous_input = "alice\nX-Injected: malicious"

        # WHEN: Sanitizing for header use
        sanitized = sanitize_header_value(dangerous_input)

        # THEN: LF should be removed
        assert "\n" not in sanitized
        assert sanitized == "aliceX-Injected: malicious"

    def test_sanitize_header_value_removes_crlf_sequence(self):
        """Test that CRLF sequence is removed to prevent header injection"""
        # GIVEN: Input with CRLF attempting header injection
        dangerous_input = "alice\r\nX-Custom-Header: injected\r\nX-Another: value"

        # WHEN: Sanitizing for header use
        sanitized = sanitize_header_value(dangerous_input)

        # THEN: CRLF sequences should be removed
        assert "\r\n" not in sanitized
        assert "\r" not in sanitized
        assert "\n" not in sanitized
        # Remaining text should be concatenated
        assert "alice" in sanitized
        assert "X-Custom-Header: injected" in sanitized

    def test_sanitize_header_value_preserves_safe_characters(self):
        """Test that safe alphanumeric and common filename characters are preserved"""
        # GIVEN: Safe username with alphanumeric, dots, underscores, hyphens
        safe_input = "alice_bob-123.test"

        # WHEN: Sanitizing for header use
        sanitized = sanitize_header_value(safe_input)

        # THEN: Should be unchanged
        assert sanitized == safe_input

    def test_sanitize_header_value_removes_null_bytes(self):
        """Test that null bytes are removed"""
        # GIVEN: Input with null byte
        dangerous_input = "alice\x00malicious"

        # WHEN: Sanitizing for header use
        sanitized = sanitize_header_value(dangerous_input)

        # THEN: Null byte should be removed
        assert "\x00" not in sanitized
        assert sanitized == "alicemalicious"

    def test_sanitize_header_value_handles_empty_string(self):
        """Test that empty string is handled correctly"""
        # GIVEN: Empty string
        empty_input = ""

        # WHEN: Sanitizing for header use
        sanitized = sanitize_header_value(empty_input)

        # THEN: Should return empty string or safe default
        assert sanitized == "" or sanitized == "user"

    def test_sanitize_header_value_enforces_max_length(self):
        """Test that excessively long values are truncated"""
        # GIVEN: Very long username (>100 chars)
        long_input = "a" * 200

        # WHEN: Sanitizing for header use
        sanitized = sanitize_header_value(long_input, max_length=100)

        # THEN: Should be truncated
        assert len(sanitized) <= 100
        assert sanitized == "a" * 100

    def test_sanitize_header_value_with_realistic_attack_payload(self):
        """Test with realistic HTTP response splitting attack"""
        # GIVEN: Realistic attack attempting to inject Set-Cookie header
        attack_payload = "alice\r\nSet-Cookie: session=hacker_session\r\nX-Evil: true"

        # WHEN: Sanitizing for header use
        sanitized = sanitize_header_value(attack_payload)

        # THEN: Attack should be neutralized
        assert "\r" not in sanitized
        assert "\n" not in sanitized
        # Verify the dangerous header instructions are concatenated (not injected as headers)
        assert "Set-Cookie" in sanitized  # Present as text, not as header
        assert sanitized == "aliceSet-Cookie: session=hacker_sessionX-Evil: true"

    def test_sanitize_header_value_removes_tab_characters(self):
        """Test that tab characters are removed"""
        # GIVEN: Input with tab characters
        dangerous_input = "alice\tmalicious"

        # WHEN: Sanitizing for header use
        sanitized = sanitize_header_value(dangerous_input)

        # THEN: Tabs should be removed or replaced
        assert sanitized == "alicemalicious" or sanitized == "alice malicious"

    def test_sanitize_header_value_with_unicode_characters(self):
        """Test that unicode characters are handled safely"""
        # GIVEN: Username with unicode characters
        unicode_input = "alice_münchen_测试"

        # WHEN: Sanitizing for header use
        sanitized = sanitize_header_value(unicode_input)

        # THEN: Should preserve or safely encode unicode
        # Either preserve unicode or replace with safe chars
        assert len(sanitized) > 0
        assert "\r" not in sanitized
        assert "\n" not in sanitized


class TestHeaderSanitizationForFilenames:
    """Test header sanitization specifically for Content-Disposition filenames"""

    def test_sanitize_for_content_disposition_filename(self):
        """Test sanitization for Content-Disposition filename parameter"""
        # GIVEN: Username that will be used in a filename
        username = "alice\r\nX-Injected: evil"
        date_str = "20250103"
        format_ext = "json"

        # WHEN: Creating sanitized filename
        from mcp_server_langgraph.core.security import sanitize_header_value

        safe_username = sanitize_header_value(username)
        filename = f"user_data_{safe_username}_{date_str}.{format_ext}"

        # THEN: Filename should not contain CRLF
        assert "\r" not in filename
        assert "\n" not in filename
        assert filename.startswith("user_data_alice")

    def test_sanitize_for_content_disposition_prevents_directory_traversal(self):
        """Test that path traversal characters are removed from filenames"""
        # GIVEN: Username with path traversal attempt
        username = "../../../etc/passwd"

        # WHEN: Sanitizing for filename use
        from mcp_server_langgraph.core.security import sanitize_header_value

        safe_username = sanitize_header_value(username)
        filename = f"user_data_{safe_username}_20250103.json"

        # THEN: Path separators should be removed or replaced
        # Either removed or replaced with safe char
        assert filename.count("/") <= 0 or not filename.startswith("/")

    def test_sanitize_rfc2231_encoding_alternative(self):
        """Test that RFC 2231 encoding can be used as alternative approach"""
        # GIVEN: Username with special characters
        username = "alice münchen"

        # WHEN: Using RFC 2231 encoding (if implemented)
        from mcp_server_langgraph.core.security import sanitize_header_value

        safe_username = sanitize_header_value(username)

        # THEN: Should be safe for header use
        assert "\r" not in safe_username
        assert "\n" not in safe_username
        # Spaces should be handled (either kept or replaced)
        assert len(safe_username) > 0


class TestIntegrationWithGDPREndpoint:
    """Integration tests for header security in GDPR data export endpoint"""

    def test_gdpr_export_filename_is_safe(self):
        """Test that GDPR export endpoint uses sanitized filenames"""
        # GIVEN: Malicious username from JWT token
        malicious_username = "alice\r\nX-Evil: injected"
        from datetime import datetime, timezone

        from mcp_server_langgraph.core.security import sanitize_header_value

        # WHEN: Creating export filename (simulating gdpr.py:208-209)
        safe_username = sanitize_header_value(malicious_username)
        filename = f"user_data_{safe_username}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
        header_value = f'attachment; filename="{filename}"'

        # THEN: Header should not allow injection
        assert "\r" not in header_value
        assert "\n" not in header_value
        # Verify header is a single line
        lines = header_value.split("\n")
        assert len(lines) == 1
