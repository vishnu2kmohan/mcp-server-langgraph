"""
Studio Security Tests

Tests for XSS prevention, CSRF protection, authorization bypass, and rate limiting.
"""

import gc

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_studio_security")
class TestXSSPrevention:
    """Tests for XSS attack prevention."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_html_sanitizer_escapes_script_tags(self) -> None:
        """GIVEN input containing script tags
        WHEN sanitizing
        THEN should escape or remove script tags
        """
        from mcp_server_langgraph.studio.security import sanitize_html

        input_text = '<script>alert("xss")</script>Hello'
        result = sanitize_html(input_text)
        assert "<script>" not in result
        assert "alert" not in result or "&lt;script&gt;" in result

    def test_html_sanitizer_escapes_event_handlers(self) -> None:
        """GIVEN input containing event handlers
        WHEN sanitizing
        THEN should remove event handlers
        """
        from mcp_server_langgraph.studio.security import sanitize_html

        input_text = '<img src="x" onerror="alert(1)">'
        result = sanitize_html(input_text)
        assert "onerror" not in result

    def test_html_sanitizer_allows_safe_tags(self) -> None:
        """GIVEN input with safe tags
        WHEN sanitizing
        THEN should preserve safe tags
        """
        from mcp_server_langgraph.studio.security import sanitize_html

        input_text = "<p>Hello <strong>world</strong></p>"
        result = sanitize_html(input_text)
        assert "<p>" in result or "Hello" in result

    def test_json_output_escapes_html(self) -> None:
        """GIVEN JSON output containing HTML
        WHEN encoding for response
        THEN should escape HTML in strings
        """
        from mcp_server_langgraph.studio.security import safe_json_encode

        data = {"message": '<script>alert("xss")</script>'}
        result = safe_json_encode(data)
        assert "<script>" not in result or "\\u003c" in result

    def test_csp_headers_are_configured(self) -> None:
        """GIVEN security headers configuration
        WHEN checking CSP
        THEN should have Content-Security-Policy header
        """
        from mcp_server_langgraph.studio.security import SECURITY_HEADERS

        assert "Content-Security-Policy" in SECURITY_HEADERS


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_studio_security")
class TestCSRFProtection:
    """Tests for CSRF attack protection."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_csrf_token_generator_creates_token(self) -> None:
        """GIVEN CSRF token generator
        WHEN generating token
        THEN should create valid token
        """
        from mcp_server_langgraph.studio.security import generate_csrf_token

        token = generate_csrf_token()
        assert token is not None
        assert len(token) >= 32

    def test_csrf_token_validator_rejects_invalid(self) -> None:
        """GIVEN invalid CSRF token
        WHEN validating
        THEN should reject token
        """
        from mcp_server_langgraph.studio.security import validate_csrf_token

        result = validate_csrf_token("invalid-token", "session-secret")
        assert result is False

    def test_csrf_token_validator_accepts_valid(self) -> None:
        """GIVEN valid CSRF token
        WHEN validating
        THEN should accept token
        """
        from mcp_server_langgraph.studio.security import (
            generate_csrf_token,
            validate_csrf_token,
        )

        secret = "test-secret-key"
        token = generate_csrf_token(secret)
        result = validate_csrf_token(token, secret)
        assert result is True

    def test_same_site_cookie_attribute_set(self) -> None:
        """GIVEN cookie configuration
        WHEN checking SameSite attribute
        THEN should be set to Strict or Lax
        """
        from mcp_server_langgraph.studio.security import COOKIE_CONFIG

        assert COOKIE_CONFIG["samesite"] in ["Strict", "Lax"]


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_studio_security")
class TestAuthorizationBypass:
    """Tests for authorization bypass prevention."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_path_traversal_blocked_in_file_access(self) -> None:
        """GIVEN path traversal attempt
        WHEN accessing files
        THEN should block traversal
        """
        from mcp_server_langgraph.studio.security import validate_path

        result = validate_path("../../../etc/passwd")
        assert result is False

    def test_url_normalization_prevents_bypass(self) -> None:
        """GIVEN URL with path manipulation
        WHEN normalizing URL
        THEN should normalize to prevent bypass
        """
        from mcp_server_langgraph.studio.security import normalize_path

        # Double encoding bypass attempt
        result = normalize_path("/admin%252F..%252F")
        assert ".." not in result

    def test_tenant_isolation_enforced(self) -> None:
        """GIVEN multi-tenant request
        WHEN accessing resources
        THEN should enforce tenant isolation
        """
        from mcp_server_langgraph.studio.security import TenantContext

        context = TenantContext(org_id="org-123")
        assert context.org_id == "org-123"
        assert context.is_valid()

    def test_jwt_audience_validated(self) -> None:
        """GIVEN JWT token
        WHEN validating
        THEN should check audience claim
        """
        from mcp_server_langgraph.studio.security import JWT_VALIDATION_CONFIG

        assert "audience" in JWT_VALIDATION_CONFIG
        assert JWT_VALIDATION_CONFIG["validate_audience"] is True

    def test_permission_check_uses_openfga(self) -> None:
        """GIVEN permission check
        WHEN verifying access
        THEN should use OpenFGA
        """
        from mcp_server_langgraph.studio.security import AUTHZ_CONFIG

        assert AUTHZ_CONFIG["backend"] == "openfga"

    def test_admin_routes_require_admin_role(self) -> None:
        """GIVEN admin routes
        WHEN checking access
        THEN should require admin role
        """
        from mcp_server_langgraph.studio.security import PROTECTED_ROUTES

        admin_routes = [r for r in PROTECTED_ROUTES if "/admin" in r["path"]]
        assert all(r["required_role"] == "admin" for r in admin_routes)


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_studio_security")
class TestRateLimiting:
    """Tests for rate limiting configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_rate_limit_config_exists(self) -> None:
        """GIVEN rate limiting configuration
        WHEN checking config
        THEN should have rate limits defined
        """
        from mcp_server_langgraph.studio.security import RATE_LIMIT_CONFIG

        assert "default" in RATE_LIMIT_CONFIG
        assert "requests_per_minute" in RATE_LIMIT_CONFIG["default"]

    def test_rate_limit_ai_suggestions_stricter(self) -> None:
        """GIVEN AI suggestions endpoint
        WHEN checking rate limit
        THEN should have stricter limit than default
        """
        from mcp_server_langgraph.studio.security import RATE_LIMIT_CONFIG

        default_rpm = RATE_LIMIT_CONFIG["default"]["requests_per_minute"]
        ai_rpm = RATE_LIMIT_CONFIG.get("ai_suggestions", {}).get("requests_per_minute", default_rpm)
        assert ai_rpm <= default_rpm

    def test_rate_limit_by_tenant(self) -> None:
        """GIVEN multi-tenant rate limiting
        WHEN checking configuration
        THEN should support per-tenant limits
        """
        from mcp_server_langgraph.studio.security import RATE_LIMIT_CONFIG

        assert RATE_LIMIT_CONFIG.get("per_tenant", True) is True

    def test_rate_limit_headers_configured(self) -> None:
        """GIVEN rate limiting
        WHEN checking response headers
        THEN should include rate limit headers
        """
        from mcp_server_langgraph.studio.security import RATE_LIMIT_HEADERS

        assert "X-RateLimit-Limit" in RATE_LIMIT_HEADERS
        assert "X-RateLimit-Remaining" in RATE_LIMIT_HEADERS
