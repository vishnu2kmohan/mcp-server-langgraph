"""
Tests for OAuth2 Authorization Code + PKCE utilities.

TDD: Write tests FIRST, then implementation.

Per RFC 9700: ROPC MUST NOT be used. Use Authorization Code + PKCE instead.
This module tests the PKCE utilities for secure OAuth2 flows.
"""

import gc
import re

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.auth]


@pytest.mark.xdist_group(name="oauth2_pkce")
class TestPKCECodeVerifier:
    """Test PKCE code verifier generation per RFC 7636."""

    def teardown_method(self) -> None:
        """Force GC to prevent accumulation in xdist workers."""
        gc.collect()

    def test_generate_code_verifier_returns_string(self):
        """Should return a string code verifier."""
        from mcp_server_langgraph.auth.oauth2 import generate_code_verifier

        verifier = generate_code_verifier()

        assert isinstance(verifier, str)
        assert len(verifier) > 0

    def test_generate_code_verifier_length_in_valid_range(self):
        """Code verifier must be 43-128 characters per RFC 7636."""
        from mcp_server_langgraph.auth.oauth2 import generate_code_verifier

        verifier = generate_code_verifier()

        # RFC 7636: code_verifier must be 43-128 characters
        assert 43 <= len(verifier) <= 128

    def test_generate_code_verifier_uses_valid_characters(self):
        """Code verifier must only use unreserved URI characters per RFC 7636."""
        from mcp_server_langgraph.auth.oauth2 import generate_code_verifier

        verifier = generate_code_verifier()

        # RFC 7636: code_verifier uses [A-Z] / [a-z] / [0-9] / "-" / "." / "_" / "~"
        valid_pattern = r"^[A-Za-z0-9\-._~]+$"
        assert re.match(valid_pattern, verifier), f"Invalid characters in verifier: {verifier}"

    def test_generate_code_verifier_is_cryptographically_random(self):
        """Each call should generate a unique verifier."""
        from mcp_server_langgraph.auth.oauth2 import generate_code_verifier

        verifiers = [generate_code_verifier() for _ in range(10)]

        # All verifiers should be unique
        assert len(set(verifiers)) == 10


@pytest.mark.xdist_group(name="oauth2_pkce")
class TestPKCECodeChallenge:
    """Test PKCE code challenge generation per RFC 7636."""

    def teardown_method(self) -> None:
        """Force GC to prevent accumulation in xdist workers."""
        gc.collect()

    def test_generate_code_challenge_returns_string(self):
        """Should return a string code challenge."""
        from mcp_server_langgraph.auth.oauth2 import generate_code_challenge

        verifier = "test-verifier-with-sufficient-length-for-testing"
        challenge = generate_code_challenge(verifier)

        assert isinstance(challenge, str)
        assert len(challenge) > 0

    def test_generate_code_challenge_uses_sha256(self):
        """Code challenge should be SHA256 hash of verifier."""
        from mcp_server_langgraph.auth.oauth2 import generate_code_challenge

        # Known test vector from RFC 7636 Appendix B
        verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        expected_challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"

        challenge = generate_code_challenge(verifier)

        assert challenge == expected_challenge

    def test_generate_code_challenge_is_base64url_encoded(self):
        """Code challenge should be base64url encoded (no padding)."""
        from mcp_server_langgraph.auth.oauth2 import generate_code_challenge

        verifier = "test-verifier-1234567890"
        challenge = generate_code_challenge(verifier)

        # base64url uses [A-Za-z0-9-_] and no '=' padding
        valid_pattern = r"^[A-Za-z0-9\-_]+$"
        assert re.match(valid_pattern, challenge), f"Invalid base64url: {challenge}"
        assert "=" not in challenge, "Challenge should not have padding"

    def test_generate_code_challenge_is_deterministic(self):
        """Same verifier should always produce same challenge."""
        from mcp_server_langgraph.auth.oauth2 import generate_code_challenge

        verifier = "my-constant-verifier-for-testing"
        challenge1 = generate_code_challenge(verifier)
        challenge2 = generate_code_challenge(verifier)

        assert challenge1 == challenge2


@pytest.mark.xdist_group(name="oauth2_pkce")
class TestBuildAuthorizationURL:
    """Test OAuth2 authorization URL construction."""

    def teardown_method(self) -> None:
        """Force GC to prevent accumulation in xdist workers."""
        gc.collect()

    def test_build_authorization_url_returns_valid_url(self):
        """Should return a valid URL string."""
        from mcp_server_langgraph.auth.oauth2 import build_authorization_url

        url = build_authorization_url(
            keycloak_url="https://keycloak.example.com",
            realm="test-realm",
            client_id="test-client",
            redirect_uri="https://app.example.com/callback",
            state="random-state-123",
            code_challenge="E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM",
        )

        assert url.startswith("https://keycloak.example.com")
        assert "/realms/test-realm/" in url

    def test_build_authorization_url_includes_required_params(self):
        """Authorization URL must include all required OAuth2 + PKCE params."""
        from mcp_server_langgraph.auth.oauth2 import build_authorization_url

        url = build_authorization_url(
            keycloak_url="https://keycloak.example.com",
            realm="test-realm",
            client_id="test-client",
            redirect_uri="https://app.example.com/callback",
            state="random-state-123",
            code_challenge="test-challenge",
        )

        # Required OAuth2 params
        assert "client_id=test-client" in url
        assert "redirect_uri=" in url
        assert "response_type=code" in url
        assert "state=random-state-123" in url

        # Required PKCE params
        assert "code_challenge=test-challenge" in url
        assert "code_challenge_method=S256" in url

    def test_build_authorization_url_includes_default_scope(self):
        """Should include default scope if not specified."""
        from mcp_server_langgraph.auth.oauth2 import build_authorization_url

        url = build_authorization_url(
            keycloak_url="https://keycloak.example.com",
            realm="test-realm",
            client_id="test-client",
            redirect_uri="https://app.example.com/callback",
            state="random-state-123",
            code_challenge="test-challenge",
        )

        # Default scope should include openid
        assert "scope=" in url
        assert "openid" in url

    def test_build_authorization_url_with_custom_scope(self):
        """Should use custom scope when provided."""
        from mcp_server_langgraph.auth.oauth2 import build_authorization_url

        url = build_authorization_url(
            keycloak_url="https://keycloak.example.com",
            realm="test-realm",
            client_id="test-client",
            redirect_uri="https://app.example.com/callback",
            state="random-state-123",
            code_challenge="test-challenge",
            scope="openid profile email custom",
        )

        assert "scope=" in url
        # URL encoded scope
        assert "openid" in url


@pytest.mark.xdist_group(name="oauth2_pkce")
class TestGenerateState:
    """Test OAuth2 state parameter generation."""

    def teardown_method(self) -> None:
        """Force GC to prevent accumulation in xdist workers."""
        gc.collect()

    def test_generate_state_returns_string(self):
        """Should return a string state parameter."""
        from mcp_server_langgraph.auth.oauth2 import generate_state

        state = generate_state()

        assert isinstance(state, str)
        assert len(state) > 0

    def test_generate_state_is_cryptographically_random(self):
        """Each call should generate a unique state."""
        from mcp_server_langgraph.auth.oauth2 import generate_state

        states = [generate_state() for _ in range(10)]

        # All states should be unique
        assert len(set(states)) == 10

    def test_generate_state_is_url_safe(self):
        """State should be URL-safe."""
        from mcp_server_langgraph.auth.oauth2 import generate_state

        state = generate_state()

        # URL-safe base64 uses [A-Za-z0-9-_]
        valid_pattern = r"^[A-Za-z0-9\-_]+$"
        assert re.match(valid_pattern, state), f"State not URL-safe: {state}"
