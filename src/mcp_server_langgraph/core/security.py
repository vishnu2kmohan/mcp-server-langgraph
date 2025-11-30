"""Security utilities for preventing common web vulnerabilities.

This module provides functions to sanitize sensitive data and prevent:
- CWE-200/CWE-532: Information Exposure Through Log Files
- CWE-113: HTTP Response Splitting
- CWE-20: Improper Input Validation

All functions are designed to be defense-in-depth security controls.
"""

from typing import Any


# Comprehensive set of sensitive field names that should be redacted in logs
# Organized by category for maintainability
SENSITIVE_FIELDS: frozenset[str] = frozenset(
    {
        # Authentication tokens
        "token",
        "access_token",
        "refresh_token",
        "bearer_token",
        "auth_token",
        "jwt",
        # Session identifiers
        "session_id",
        "session_token",
        # Credentials and secrets
        "password",
        "secret",
        "secret_key",
        "client_secret",
        "api_key",
        "api_key_value",
        "private_key",
        "credentials",
        "credential",
        # User PII (GDPR/CCPA/HIPAA)
        "user_id",
        "username",
        # HTTP headers containing credentials
        "authorization",
    }
)

# Fields that should be truncated rather than redacted
TRUNCATABLE_FIELDS: frozenset[str] = frozenset(
    {
        "message",
        "query",
    }
)


def sanitize_for_logging(arguments: dict[str, Any], max_length: int = 500) -> dict[str, Any]:
    """Sanitize sensitive data from arguments before logging.

    Prevents CWE-200 (Information Exposure) and CWE-532 (Information Exposure Through Log Files)
    by redacting authentication tokens, session identifiers, credentials, and PII,
    plus truncating large text fields.

    This function creates a shallow copy of the input dict and applies the following
    transformations:
    - Redacts all fields in SENSITIVE_FIELDS to prevent credential/PII exposure
    - Truncates fields in TRUNCATABLE_FIELDS that exceed max_length
    - Preserves all other fields as-is (shallow copy)

    Args:
        arguments: Dictionary of tool call arguments or log context
        max_length: Maximum length for text fields before truncation (default: 500)

    Returns:
        Sanitized copy of arguments safe for logging

    Example:
        >>> args = {"token": "secret_jwt", "api_key": "sk_live_123", "password": "pass123"}
        >>> sanitized = sanitize_for_logging(args)
        >>> sanitized
        {"token": "[REDACTED]", "api_key": "[REDACTED]", "password": "[REDACTED]"}
        >>> args["token"]  # Original unchanged
        "secret_jwt"

    Security Context:
        - JWT tokens in logs can be extracted and replayed to impersonate users
        - Session IDs in logs enable session hijacking if logs are compromised
        - API keys allow unauthorized access to external services
        - Passwords enable account compromise
        - Client secrets compromise OAuth flows
        - Usernames/user IDs are PII subject to GDPR/CCPA/HIPAA protection
        - Large prompts may contain sensitive user data (PII, credentials, secrets)
        - Centralized logging systems may have broader access than application logs
        - Compliance frameworks (SOC2, PCI-DSS, HIPAA) require credential protection

    Thread Safety:
        This function is thread-safe as it creates a new dict (shallow copy).
    """
    # Create shallow copy to avoid modifying original
    sanitized = arguments.copy()

    # Redact all sensitive fields
    for field in SENSITIVE_FIELDS:
        if field in sanitized and sanitized[field] is not None:
            sanitized[field] = "[REDACTED]"

    # Truncate long text fields
    for field in TRUNCATABLE_FIELDS:
        if field in sanitized and isinstance(sanitized[field], str) and len(sanitized[field]) > max_length:
            sanitized[field] = sanitized[field][:max_length] + "..."

    return sanitized


def sanitize_header_value(value: str, max_length: int = 100) -> str:
    """Sanitize user-controlled strings for safe use in HTTP headers.

    Prevents CWE-113 (HTTP Response Splitting) by removing control characters
    that could be used to inject additional headers or alter HTTP responses.

    This function is specifically designed for values used in HTTP headers
    like Content-Disposition filenames, where user-controlled data (e.g.,
    usernames from JWT tokens) may be incorporated.

    Args:
        value: User-controlled string to sanitize (e.g., username)
        max_length: Maximum allowed length (default: 100)

    Returns:
        Sanitized string safe for use in HTTP header values

    Example:
        >>> username = "alice\\r\\nX-Evil: injected"
        >>> safe = sanitize_header_value(username)
        >>> safe
        "aliceX-Evil: injected"  # CRLF removed, attack neutralized

    Security Context:
        HTTP Response Splitting Attack:
        1. Attacker registers username: "alice\\r\\nSet-Cookie: session=hacked"
        2. Server creates header: Content-Disposition: attachment; filename="user_data_alice
           Set-Cookie: session=hacked_20250103.json"
        3. Browser interprets this as TWO headers (response split)
        4. Attacker successfully injects malicious Set-Cookie header

        This function prevents the attack by removing CR/LF characters.

    Related Vulnerabilities:
        - CWE-113: Improper Neutralization of CRLF Sequences in HTTP Headers
        - SANS Top 25: Improper Input Validation
        - OWASP: HTTP Response Splitting

    Thread Safety:
        This function is thread-safe (no shared state).
    """
    if not value:
        return ""

    # Remove all control characters that could split HTTP headers
    # CR (\\r), LF (\\n), NULL (\\x00), TAB (\\t)
    sanitized = value

    # Remove carriage return and line feed (primary attack vectors)
    sanitized = sanitized.replace("\r", "")
    sanitized = sanitized.replace("\n", "")

    # Remove null bytes
    sanitized = sanitized.replace("\x00", "")

    # Replace tabs with spaces (preserve readability)
    sanitized = sanitized.replace("\t", " ")

    # Remove path traversal sequences for filename safety
    sanitized = sanitized.replace("../", "")
    sanitized = sanitized.replace("..\\", "")

    # Enforce maximum length to prevent DoS
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]

    # Remove leading/trailing whitespace
    sanitized = sanitized.strip()

    return sanitized
