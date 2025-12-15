"""
Tests for session fingerprinting (device/browser binding).

TDD: Tests for session fingerprint generation and validation.
Per OWASP Session Management: Bind sessions to device characteristics
to detect session hijacking attempts.
"""

import gc

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.auth]


@pytest.mark.xdist_group(name="session_fingerprint")
class TestSessionFingerprintGeneration:
    """Tests for generating session fingerprints from request headers."""

    def teardown_method(self) -> None:
        """Force GC to prevent accumulation in xdist workers."""
        gc.collect()

    def test_generate_fingerprint_from_user_agent(self):
        """
        GIVEN: Request headers with User-Agent
        WHEN: generate_session_fingerprint() is called
        THEN: Should include User-Agent hash in fingerprint
        """
        from mcp_server_langgraph.auth.session_fingerprint import generate_session_fingerprint

        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
        }

        fingerprint = generate_session_fingerprint(headers)

        assert fingerprint is not None
        assert len(fingerprint) > 0
        # Fingerprint should be deterministic
        fingerprint2 = generate_session_fingerprint(headers)
        assert fingerprint == fingerprint2

    def test_generate_fingerprint_includes_accept_language(self):
        """
        GIVEN: Request headers with Accept-Language
        WHEN: generate_session_fingerprint() is called
        THEN: Different languages should produce different fingerprints
        """
        from mcp_server_langgraph.auth.session_fingerprint import generate_session_fingerprint

        headers_en = {
            "user-agent": "Mozilla/5.0",
            "accept-language": "en-US,en;q=0.9",
        }
        headers_fr = {
            "user-agent": "Mozilla/5.0",
            "accept-language": "fr-FR,fr;q=0.9",
        }

        fingerprint_en = generate_session_fingerprint(headers_en)
        fingerprint_fr = generate_session_fingerprint(headers_fr)

        assert fingerprint_en != fingerprint_fr

    def test_generate_fingerprint_handles_missing_headers(self):
        """
        GIVEN: Empty or missing headers
        WHEN: generate_session_fingerprint() is called
        THEN: Should return a valid fingerprint (empty headers case)
        """
        from mcp_server_langgraph.auth.session_fingerprint import generate_session_fingerprint

        fingerprint = generate_session_fingerprint({})

        # Should return a fingerprint even with no headers
        assert fingerprint is not None
        assert len(fingerprint) > 0

    def test_fingerprint_is_hashed_not_plain(self):
        """
        GIVEN: Request headers
        WHEN: generate_session_fingerprint() is called
        THEN: Should return a hash, not plain header values
        """
        from mcp_server_langgraph.auth.session_fingerprint import generate_session_fingerprint

        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        }

        fingerprint = generate_session_fingerprint(headers)

        # Fingerprint should not contain raw header values
        assert "Mozilla" not in fingerprint
        assert "Windows" not in fingerprint
        # Should be a hash (hex string)
        assert all(c in "0123456789abcdef" for c in fingerprint.lower())


@pytest.mark.xdist_group(name="session_fingerprint")
class TestSessionFingerprintValidation:
    """Tests for validating session fingerprints."""

    def teardown_method(self) -> None:
        """Force GC to prevent accumulation in xdist workers."""
        gc.collect()

    def test_validate_fingerprint_with_matching_headers(self):
        """
        GIVEN: Original fingerprint and same request headers
        WHEN: validate_session_fingerprint() is called
        THEN: Should return True (valid)
        """
        from mcp_server_langgraph.auth.session_fingerprint import (
            generate_session_fingerprint,
            validate_session_fingerprint,
        )

        headers = {
            "user-agent": "Mozilla/5.0 Chrome/120.0.0.0",
            "accept-language": "en-US,en;q=0.9",
        }

        original_fingerprint = generate_session_fingerprint(headers)
        is_valid = validate_session_fingerprint(original_fingerprint, headers)

        assert is_valid is True

    def test_validate_fingerprint_with_different_user_agent_fails(self):
        """
        GIVEN: Original fingerprint and different User-Agent
        WHEN: validate_session_fingerprint() is called
        THEN: Should return False (potential hijacking)
        """
        from mcp_server_langgraph.auth.session_fingerprint import (
            generate_session_fingerprint,
            validate_session_fingerprint,
        )

        original_headers = {
            "user-agent": "Mozilla/5.0 Chrome/120.0.0.0",
            "accept-language": "en-US",
        }
        attacker_headers = {
            "user-agent": "Mozilla/5.0 Firefox/121.0",
            "accept-language": "en-US",
        }

        original_fingerprint = generate_session_fingerprint(original_headers)
        is_valid = validate_session_fingerprint(original_fingerprint, attacker_headers)

        assert is_valid is False

    def test_validate_fingerprint_with_different_language_fails(self):
        """
        GIVEN: Original fingerprint and different Accept-Language
        WHEN: validate_session_fingerprint() is called
        THEN: Should return False (potential hijacking)
        """
        from mcp_server_langgraph.auth.session_fingerprint import (
            generate_session_fingerprint,
            validate_session_fingerprint,
        )

        original_headers = {
            "user-agent": "Mozilla/5.0",
            "accept-language": "en-US,en;q=0.9",
        }
        attacker_headers = {
            "user-agent": "Mozilla/5.0",
            "accept-language": "ru-RU,ru;q=0.9",
        }

        original_fingerprint = generate_session_fingerprint(original_headers)
        is_valid = validate_session_fingerprint(original_fingerprint, attacker_headers)

        assert is_valid is False

    def test_validate_fingerprint_with_none_fingerprint(self):
        """
        GIVEN: None as original fingerprint
        WHEN: validate_session_fingerprint() is called
        THEN: Should return True (no fingerprint to validate)
        """
        from mcp_server_langgraph.auth.session_fingerprint import validate_session_fingerprint

        headers = {"user-agent": "Mozilla/5.0"}

        # No fingerprint stored - validation passes (backward compatibility)
        is_valid = validate_session_fingerprint(None, headers)

        assert is_valid is True

    def test_validate_fingerprint_with_empty_fingerprint(self):
        """
        GIVEN: Empty string as original fingerprint
        WHEN: validate_session_fingerprint() is called
        THEN: Should return True (no fingerprint to validate)
        """
        from mcp_server_langgraph.auth.session_fingerprint import validate_session_fingerprint

        headers = {"user-agent": "Mozilla/5.0"}

        is_valid = validate_session_fingerprint("", headers)

        assert is_valid is True


@pytest.mark.xdist_group(name="session_fingerprint")
class TestFingerprintConfiguration:
    """Tests for fingerprint configuration options."""

    def teardown_method(self) -> None:
        """Force GC to prevent accumulation in xdist workers."""
        gc.collect()

    def test_fingerprint_includes_configured_headers(self):
        """
        GIVEN: Custom list of headers to include
        WHEN: generate_session_fingerprint() is called with include_headers
        THEN: Should only use specified headers
        """
        from mcp_server_langgraph.auth.session_fingerprint import generate_session_fingerprint

        headers = {
            "user-agent": "Mozilla/5.0",
            "accept-language": "en-US",
            "accept-encoding": "gzip, deflate",
        }

        # Only fingerprint user-agent
        fp1 = generate_session_fingerprint(headers, include_headers=["user-agent"])

        # Fingerprint user-agent + accept-language
        fp2 = generate_session_fingerprint(headers, include_headers=["user-agent", "accept-language"])

        # Different headers included should produce different fingerprints
        assert fp1 != fp2

    def test_fingerprint_is_case_insensitive_for_header_names(self):
        """
        GIVEN: Headers with different case
        WHEN: generate_session_fingerprint() is called
        THEN: Should produce same fingerprint regardless of case
        """
        from mcp_server_langgraph.auth.session_fingerprint import generate_session_fingerprint

        headers_lower = {"user-agent": "Mozilla/5.0"}
        headers_upper = {"User-Agent": "Mozilla/5.0"}

        fp_lower = generate_session_fingerprint(headers_lower)
        fp_upper = generate_session_fingerprint(headers_upper)

        assert fp_lower == fp_upper
