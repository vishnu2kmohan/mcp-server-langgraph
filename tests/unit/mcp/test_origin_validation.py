"""
Tests for MCP HTTP 403 Origin Validation.

MCP 2025-11-25 specifies that servers should return HTTP 403 for invalid
Origin headers in HTTP requests.

TDD: RED phase - Define expected behavior for origin validation.
"""

import pytest

pytestmark = pytest.mark.unit


class TestOriginValidator:
    """Test origin validation logic."""

    def test_validate_origin_allowed_single(self) -> None:
        """Should allow origin that matches single allowed origin."""
        from mcp_server_langgraph.mcp.origin_validation import validate_origin

        allowed_origins = ["https://example.com"]
        result = validate_origin("https://example.com", allowed_origins)

        assert result is True

    def test_validate_origin_allowed_multiple(self) -> None:
        """Should allow origin from list of allowed origins."""
        from mcp_server_langgraph.mcp.origin_validation import validate_origin

        allowed_origins = [
            "https://app.example.com",
            "https://admin.example.com",
            "http://localhost:3000",
        ]
        result = validate_origin("https://admin.example.com", allowed_origins)

        assert result is True

    def test_validate_origin_not_allowed(self) -> None:
        """Should reject origin not in allowed list."""
        from mcp_server_langgraph.mcp.origin_validation import validate_origin

        allowed_origins = ["https://example.com"]
        result = validate_origin("https://malicious.com", allowed_origins)

        assert result is False

    def test_validate_origin_none_allowed(self) -> None:
        """Should allow any origin when allowed list is empty."""
        from mcp_server_langgraph.mcp.origin_validation import validate_origin

        allowed_origins: list[str] = []
        result = validate_origin("https://any-origin.com", allowed_origins)

        assert result is True

    def test_validate_origin_wildcard(self) -> None:
        """Should allow any origin when wildcard is in list."""
        from mcp_server_langgraph.mcp.origin_validation import validate_origin

        allowed_origins = ["*"]
        result = validate_origin("https://any-origin.com", allowed_origins)

        assert result is True

    def test_validate_origin_missing_origin_header(self) -> None:
        """Should allow request with no Origin header."""
        from mcp_server_langgraph.mcp.origin_validation import validate_origin

        allowed_origins = ["https://example.com"]
        result = validate_origin(None, allowed_origins)

        # No origin header means same-origin request, should be allowed
        assert result is True


class TestOriginValidationResponse:
    """Test origin validation error response format."""

    def test_create_forbidden_response(self) -> None:
        """Should create HTTP 403 forbidden response."""
        from mcp_server_langgraph.mcp.origin_validation import (
            create_origin_forbidden_response,
        )

        response = create_origin_forbidden_response("https://bad-origin.com")

        assert response["status_code"] == 403
        assert response["body"]["error"] == "Forbidden"
        assert "bad-origin.com" in response["body"]["message"]

    def test_forbidden_response_content_type(self) -> None:
        """Forbidden response should be JSON."""
        from mcp_server_langgraph.mcp.origin_validation import (
            create_origin_forbidden_response,
        )

        response = create_origin_forbidden_response("https://evil.com")

        assert response["content_type"] == "application/json"


class TestOriginValidationMiddleware:
    """Test origin validation middleware helper."""

    def test_should_validate_origin_for_post(self) -> None:
        """Should validate origin for POST requests."""
        from mcp_server_langgraph.mcp.origin_validation import should_validate_origin

        assert should_validate_origin("POST") is True

    def test_should_validate_origin_for_put(self) -> None:
        """Should validate origin for PUT requests."""
        from mcp_server_langgraph.mcp.origin_validation import should_validate_origin

        assert should_validate_origin("PUT") is True

    def test_should_not_validate_origin_for_get(self) -> None:
        """Should not validate origin for GET requests (read-only)."""
        from mcp_server_langgraph.mcp.origin_validation import should_validate_origin

        assert should_validate_origin("GET") is False

    def test_should_not_validate_origin_for_options(self) -> None:
        """Should not validate origin for OPTIONS (CORS preflight)."""
        from mcp_server_langgraph.mcp.origin_validation import should_validate_origin

        assert should_validate_origin("OPTIONS") is False
