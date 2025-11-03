"""Security utilities for preventing CWE-200/CWE-532 vulnerabilities.

This module provides functions to sanitize sensitive data before logging,
preventing credential exposure and information leakage through application logs.
"""

from typing import Any


def sanitize_for_logging(arguments: dict[str, Any], max_length: int = 500) -> dict[str, Any]:
    """Sanitize sensitive data from arguments before logging.

    Prevents CWE-200 (Information Exposure) and CWE-532 (Information Exposure Through Log Files)
    by redacting authentication tokens and truncating large text fields.

    This function creates a shallow copy of the input dict and applies the following
    transformations:
    - Redacts 'token' field value to prevent JWT/credential exposure
    - Truncates 'message' and 'query' fields that exceed max_length
    - Preserves all other fields as-is (shallow copy)

    Args:
        arguments: Dictionary of tool call arguments or log context
        max_length: Maximum length for text fields before truncation (default: 500)

    Returns:
        Sanitized copy of arguments safe for logging

    Example:
        >>> args = {"token": "secret_jwt", "message": "Hello"}
        >>> sanitized = sanitize_for_logging(args)
        >>> sanitized
        {"token": "[REDACTED]", "message": "Hello"}
        >>> args["token"]  # Original unchanged
        "secret_jwt"

    Security Context:
        - JWT tokens in logs can be extracted and replayed to impersonate users
        - Large prompts may contain sensitive user data (PII, credentials, secrets)
        - Centralized logging systems may have broader access than application logs
        - Compliance frameworks (SOC2, PCI-DSS, HIPAA) require credential protection

    Thread Safety:
        This function is thread-safe as it creates a new dict (shallow copy).
    """
    # Create shallow copy to avoid modifying original
    sanitized = arguments.copy()

    # Redact authentication token
    if "token" in sanitized and sanitized["token"] is not None:
        sanitized["token"] = "[REDACTED]"

    # Truncate long message fields
    if "message" in sanitized and isinstance(sanitized["message"], str):
        if len(sanitized["message"]) > max_length:
            sanitized["message"] = sanitized["message"][:max_length] + "..."

    # Truncate long query fields
    if "query" in sanitized and isinstance(sanitized["query"], str):
        if len(sanitized["query"]) > max_length:
            sanitized["query"] = sanitized["query"][:max_length] + "..."

    return sanitized
