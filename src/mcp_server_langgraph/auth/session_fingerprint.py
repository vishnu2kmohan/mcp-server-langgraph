"""
Session Fingerprinting for Device/Browser Binding.

Per OWASP Session Management Cheat Sheet:
- Bind sessions to client characteristics to detect session hijacking
- Include User-Agent, Accept-Language, and other stable headers
- Use hashing to avoid storing raw header values

This module provides:
- generate_session_fingerprint(): Create fingerprint from request headers
- validate_session_fingerprint(): Verify fingerprint matches current request
"""

import hashlib
from typing import Any

# Default headers to include in fingerprint
# These are typically stable for a browser session
DEFAULT_FINGERPRINT_HEADERS = [
    "user-agent",
    "accept-language",
]


def generate_session_fingerprint(
    headers: dict[str, Any],
    include_headers: list[str] | None = None,
) -> str:
    """
    Generate a session fingerprint from request headers.

    The fingerprint is a SHA-256 hash of selected request headers that are
    typically stable for a browser session. This helps detect session hijacking
    when the attacker uses a different browser/device.

    Args:
        headers: Dictionary of request headers (case-insensitive keys)
        include_headers: Optional list of headers to include. Defaults to
                        User-Agent and Accept-Language.

    Returns:
        Hex-encoded SHA-256 hash of the fingerprint data.

    Example:
        >>> headers = {"user-agent": "Mozilla/5.0", "accept-language": "en-US"}
        >>> fp = generate_session_fingerprint(headers)
        >>> # Returns something like "a3f2b1c4d5..."
    """
    if include_headers is None:
        include_headers = DEFAULT_FINGERPRINT_HEADERS

    # Normalize headers to lowercase keys for case-insensitive matching
    normalized_headers = {k.lower(): v for k, v in headers.items()}

    # Build fingerprint data from selected headers
    fingerprint_parts = []
    for header_name in sorted(include_headers):  # Sort for deterministic ordering
        header_key = header_name.lower()
        value = normalized_headers.get(header_key, "")
        if value:
            # Include header name and value in fingerprint
            fingerprint_parts.append(f"{header_key}:{value}")

    # Join all parts and hash
    fingerprint_data = "|".join(fingerprint_parts)

    # Use SHA-256 for the hash
    return hashlib.sha256(fingerprint_data.encode("utf-8")).hexdigest()


def validate_session_fingerprint(
    original_fingerprint: str | None,
    current_headers: dict[str, Any],
    include_headers: list[str] | None = None,
) -> bool:
    """
    Validate that the current request fingerprint matches the original.

    This should be called on each request to detect potential session hijacking.
    If the fingerprints don't match, the session may have been stolen.

    Args:
        original_fingerprint: The fingerprint stored when session was created.
                             If None or empty, validation passes (backward compat).
        current_headers: Dictionary of current request headers.
        include_headers: Optional list of headers to include. Must match the
                        headers used when creating the original fingerprint.

    Returns:
        True if fingerprints match or no original fingerprint exists.
        False if fingerprints don't match (potential hijacking).

    Example:
        >>> # On session creation:
        >>> fp = generate_session_fingerprint(headers)
        >>> session.metadata["fingerprint"] = fp
        >>>
        >>> # On subsequent requests:
        >>> if not validate_session_fingerprint(session.metadata.get("fingerprint"), headers):
        >>>     raise SessionHijackingDetected()
    """
    # If no original fingerprint, skip validation (backward compatibility)
    if not original_fingerprint:
        return True

    # Generate fingerprint from current headers
    current_fingerprint = generate_session_fingerprint(current_headers, include_headers=include_headers)

    # Compare fingerprints (constant-time comparison for security)
    return _constant_time_compare(original_fingerprint, current_fingerprint)


def _constant_time_compare(a: str, b: str) -> bool:
    """
    Compare two strings in constant time to prevent timing attacks.

    Args:
        a: First string
        b: Second string

    Returns:
        True if strings are equal, False otherwise.
    """
    if len(a) != len(b):
        return False

    result = 0
    for x, y in zip(a, b, strict=True):
        result |= ord(x) ^ ord(y)

    return result == 0


# Re-export for convenience
__all__ = [
    "generate_session_fingerprint",
    "validate_session_fingerprint",
    "DEFAULT_FINGERPRINT_HEADERS",
]
