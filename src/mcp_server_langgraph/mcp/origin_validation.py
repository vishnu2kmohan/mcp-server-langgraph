"""
MCP HTTP 403 Origin Validation.

MCP 2025-11-25 specifies that servers should return HTTP 403 for invalid
Origin headers in HTTP requests. This module provides utilities for
origin validation in MCP HTTP transport.

Reference: https://modelcontextprotocol.io/specification/2025-11-25
"""

from typing import Any


def validate_origin(origin: str | None, allowed_origins: list[str]) -> bool:
    """Validate if an Origin header is allowed.

    Args:
        origin: Origin header value from request (None if not present)
        allowed_origins: List of allowed origin patterns

    Returns:
        True if origin is allowed, False otherwise

    Note:
        - Empty allowed_origins list means all origins are allowed
        - "*" in allowed_origins means all origins are allowed
        - Missing Origin header (None) is allowed (same-origin request)
    """
    # No Origin header means same-origin request, always allowed
    if origin is None:
        return True

    # Empty list means no restrictions
    if not allowed_origins:
        return True

    # Check for wildcard
    if "*" in allowed_origins:
        return True

    # Check if origin is in allowed list (exact match)
    return origin in allowed_origins


def create_origin_forbidden_response(origin: str) -> dict[str, Any]:
    """Create HTTP 403 Forbidden response for invalid origin.

    Args:
        origin: The invalid origin that was rejected

    Returns:
        Dict with status_code, content_type, and body for response
    """
    return {
        "status_code": 403,
        "content_type": "application/json",
        "body": {
            "error": "Forbidden",
            "message": f"Origin '{origin}' is not allowed",
        },
    }


def should_validate_origin(method: str) -> bool:
    """Determine if origin should be validated for HTTP method.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE, OPTIONS, etc.)

    Returns:
        True if origin validation should be performed

    Note:
        Origin validation is only needed for state-changing requests.
        GET (read-only) and OPTIONS (CORS preflight) are exempt.
    """
    # Safe methods don't need origin validation
    safe_methods = {"GET", "HEAD", "OPTIONS"}
    return method.upper() not in safe_methods
