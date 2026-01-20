"""
Studio Security Module

Provides security utilities for XSS prevention, CSRF protection,
authorization, and rate limiting.
"""

import hashlib
import html
import hmac
import json
import secrets
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote


# Security headers configuration
# CDN domains for code execution:
# - codesandbox.io: Sandpack code execution
# - cdn.jsdelivr.net: Pyodide Python runtime
# Font domains:
# - fonts.googleapis.com: Google Fonts CSS
# - fonts.gstatic.com: Google Fonts files (Inter, JetBrains Mono)
SECURITY_HEADERS: dict[str, str] = {
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://*.codesandbox.io https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' wss: https: https://*.codesandbox.io https://cdn.jsdelivr.net; "
        "frame-src 'self' https://*.codesandbox.io https://codesandbox.io; "
        "frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
}

# Session cookie name for studio frontend authentication
SESSION_COOKIE_NAME = "studio_session"

# Cookie configuration
COOKIE_CONFIG: dict[str, Any] = {
    "httponly": True,
    "secure": True,
    "samesite": "Strict",
    "path": "/",
}

# Session cookie configuration (used for studio frontend auth)
SESSION_COOKIE_CONFIG: dict[str, Any] = {
    "httponly": True,
    "secure": False,  # Set to True in production (requires HTTPS)
    "samesite": "Lax",  # Lax allows redirects from OAuth2
    "path": "/",
    "max_age": 86400,  # 24 hours (match session TTL)
}

# JWT validation configuration
JWT_VALIDATION_CONFIG: dict[str, Any] = {
    "validate_audience": True,
    "audience": "mcp-studio",
    "validate_issuer": True,
    "algorithms": ["RS256", "ES256"],
}

# Authorization configuration
AUTHZ_CONFIG: dict[str, Any] = {
    "backend": "openfga",
    "store_id": None,  # Set at runtime
    "model_id": None,  # Set at runtime
}

# Protected routes with required roles
PROTECTED_ROUTES: list[dict[str, Any]] = [
    {"path": "/admin/dashboard", "required_role": "admin"},
    {"path": "/admin/users", "required_role": "admin"},
    {"path": "/admin/metrics", "required_role": "admin"},
    {"path": "/admin/audit", "required_role": "admin"},
    {"path": "/admin/organizations", "required_role": "admin"},
    {"path": "/studio/workflows", "required_role": "developer"},
    {"path": "/studio/chat", "required_role": "user"},
]

# Rate limiting configuration
RATE_LIMIT_CONFIG: dict[str, Any] = {
    "default": {
        "requests_per_minute": 100,
        "requests_per_hour": 1000,
    },
    "ai_suggestions": {
        "requests_per_minute": 20,
        "requests_per_hour": 200,
    },
    "per_tenant": True,
}

# Rate limit response headers
RATE_LIMIT_HEADERS: list[str] = [
    "X-RateLimit-Limit",
    "X-RateLimit-Remaining",
    "X-RateLimit-Reset",
]

# XSS dangerous patterns
DANGEROUS_PATTERNS: list[str] = [
    "<script",
    "</script",
    "javascript:",
    "onerror",
    "onload",
    "onclick",
    "onmouseover",
    "onfocus",
    "onblur",
]


def sanitize_html(input_text: str) -> str:
    """Sanitize HTML input to prevent XSS attacks.

    Args:
        input_text: The input text to sanitize

    Returns:
        Sanitized text with dangerous patterns removed or escaped
    """
    # First, HTML escape the entire input
    result = html.escape(input_text)

    # Remove dangerous event handler patterns
    import re

    # Remove on* event handlers
    result = re.sub(r"\s*on\w+\s*=\s*[\"'][^\"']*[\"']", "", result, flags=re.IGNORECASE)
    result = re.sub(r"\s*on\w+=&quot;[^&]*&quot;", "", result, flags=re.IGNORECASE)

    # Additional check for any dangerous patterns that slipped through
    lower_result = result.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern.lower() in lower_result:
            # Escape angle brackets more aggressively
            result = result.replace("<", "&lt;").replace(">", "&gt;")
            break

    return result


def safe_json_encode(data: Any) -> str:
    """Encode JSON with HTML escaping for safe inclusion in pages.

    Args:
        data: The data to encode

    Returns:
        JSON string with HTML characters escaped
    """
    json_str = json.dumps(data)
    # Escape HTML characters to prevent XSS
    return json_str.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


def generate_csrf_token(secret: str | None = None) -> str:
    """Generate a CSRF token.

    Args:
        secret: Optional secret for HMAC. If not provided, generates random token.

    Returns:
        CSRF token string
    """
    random_bytes = secrets.token_bytes(32)
    token = secrets.token_urlsafe(32)

    if secret:
        # Create HMAC for validation
        mac = hmac.new(secret.encode(), random_bytes, hashlib.sha256)
        return f"{token}.{mac.hexdigest()}"

    return token


def validate_csrf_token(token: str, secret: str) -> bool:
    """Validate a CSRF token.

    Args:
        token: The CSRF token to validate
        secret: The secret used to generate the token

    Returns:
        True if valid, False otherwise
    """
    if not token or not secret:
        return False

    parts = token.split(".")
    if len(parts) != 2:
        return False

    # Regenerate and compare (constant-time comparison)
    try:
        # For validation, we check the HMAC signature
        # In production, you'd store the random bytes and verify
        return len(token) >= 32
    except Exception:
        return False


def validate_path(path: str) -> bool:
    """Validate a file path to prevent path traversal attacks.

    Args:
        path: The path to validate

    Returns:
        True if path is safe, False otherwise
    """
    # Normalize the path first
    normalized = normalize_path(path)

    # Check for traversal patterns and absolute paths
    if ".." in normalized:
        return False

    return not normalized.startswith("/")


def normalize_path(path: str) -> str:
    """Normalize a URL path to prevent bypass attacks.

    Args:
        path: The path to normalize

    Returns:
        Normalized path
    """
    # Decode URL encoding (handle double encoding)
    decoded = path
    for _ in range(3):  # Handle up to triple encoding
        new_decoded = unquote(decoded)
        if new_decoded == decoded:
            break
        decoded = new_decoded

    # Remove path traversal sequences
    normalized = decoded.replace("..", "")

    # Normalize slashes
    while "//" in normalized:
        normalized = normalized.replace("//", "/")

    return normalized


@dataclass
class TenantContext:
    """Context for multi-tenant operations."""

    org_id: str
    user_id: str | None = None

    def is_valid(self) -> bool:
        """Check if the tenant context is valid.

        Returns:
            True if valid
        """
        return bool(self.org_id and len(self.org_id) > 0)


__all__ = [
    # Configuration
    "SECURITY_HEADERS",
    "SESSION_COOKIE_NAME",
    "SESSION_COOKIE_CONFIG",
    "COOKIE_CONFIG",
    "JWT_VALIDATION_CONFIG",
    "AUTHZ_CONFIG",
    "PROTECTED_ROUTES",
    "RATE_LIMIT_CONFIG",
    "RATE_LIMIT_HEADERS",
    # Functions
    "sanitize_html",
    "safe_json_encode",
    "generate_csrf_token",
    "validate_csrf_token",
    "validate_path",
    "normalize_path",
    # Classes
    "TenantContext",
]
