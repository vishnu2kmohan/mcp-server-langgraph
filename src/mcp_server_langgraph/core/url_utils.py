"""URL encoding utilities for Redis connection strings.

This module provides utilities to ensure Redis connection URLs have properly
percent-encoded passwords per RFC 3986, preventing parsing errors when passwords
contain special characters like /, +, =, etc.

Background:
-----------
Production incident with revision 758b8f744 where unencoded special characters
in Redis password caused ValueError during redis.connection.parse_url():
"Port could not be cast to integer value as 'Du0PmDvmqDWqDTgfGnmi6'"

The password "Du0PmDvmqDWqDTgfGnmi6/SKyuQydi3z7cPTgEQoE+s=" contained unencoded
/ and + characters, causing the URL parser to misinterpret the password as
host/port components.

Solution:
---------
Percent-encode all special characters in the password component:
- / → %2F
- + → %2B
- = → %3D
- @ → %40
- etc.

References:
-----------
- RFC 3986: Uniform Resource Identifier (URI): Generic Syntax
- Redis URL format: redis://[user]:[password]@[host]:[port]/[database]
"""

from urllib.parse import quote, unquote


def ensure_redis_password_encoded(redis_url: str) -> str:
    """Ensure Redis password in URL is properly percent-encoded per RFC 3986.

    This function provides defense-in-depth URL encoding for Redis connection
    strings. It handles cases where passwords contain special characters that
    would otherwise break URL parsing (/, +, =, @, etc.).

    The function is idempotent - running it multiple times on the same URL
    produces the same result (already-encoded passwords are not double-encoded).

    Args:
        redis_url: Redis connection URL in format:
                   redis://[username]:[password]@[host]:[port]/[database]
                   Examples:
                   - redis://:mypassword@localhost:6379/1
                   - redis://user:pass@redis-host:6380/0
                   - redis://localhost:6379/1  (no auth)

    Returns:
        URL with properly percent-encoded password component. All other
        components (scheme, host, port, database) remain unchanged.

    Examples:
        >>> ensure_redis_password_encoded("redis://:pass/word@localhost:6379/1")
        'redis://:pass%2Fword@localhost:6379/1'

        >>> ensure_redis_password_encoded("redis://:p+w=d@host:6379/0")
        'redis://:p%2Bw%3Dd@host:6379/0'

        >>> ensure_redis_password_encoded("redis://localhost:6379/1")
        'redis://localhost:6379/1'

    Notes:
        - Uses empty safe='' parameter to urllib.parse.quote to encode ALL
          special characters, ensuring maximum compatibility
        - Preserves username if present
        - Does not modify URLs without passwords
        - Handles edge cases: empty password, no auth, etc.
        - Uses regex for manual parsing because urlparse() fails on
          unencoded special characters in passwords
    """
    # Redis URL pattern: redis://[username]:[password]@host:port/database
    # We need to manually parse this because urlparse() fails when password
    # contains unencoded special characters like / or @

    # Strategy: Find the LAST @ in the URL (before any # fragment)
    # This @ separates credentials from host, even if @ appears in password
    if "@" not in redis_url:
        # No authentication
        return redis_url

    # Split on scheme
    if not redis_url.startswith("redis://"):
        return redis_url

    after_scheme = redis_url[8:]  # Remove 'redis://'

    # Find the LAST @ in the entire string (handles @ in password)
    # The rightmost @ is the delimiter between auth and host
    at_pos = after_scheme.rfind("@")
    if at_pos == -1:
        # No @ found (shouldn't happen given earlier check, but defensive)
        return redis_url

    credentials = after_scheme[:at_pos]
    rest = after_scheme[at_pos + 1 :]  # Everything after @

    # Parse credentials as username:password or :password
    if ":" not in credentials:
        # Just username, no password (unusual for Redis but valid)
        return redis_url

    # Split on FIRST : to separate username from password
    # (password might contain : as well)
    colon_pos = credentials.find(":")
    username = credentials[:colon_pos] if colon_pos > 0 else ""
    password = credentials[colon_pos + 1 :]

    if not password:
        # Empty password
        return redis_url

    # Check if password is already encoded (idempotent behavior)
    # If unquote changes the string, it was encoded; if not, it's raw
    # We'll encode it regardless, but first decode if already encoded
    # to avoid double-encoding
    try:
        # Try to decode the password
        decoded_password = unquote(password)
        # Now encode it properly (whether it was encoded or not)
        encoded_password = quote(decoded_password, safe="")
    except Exception:
        # If decoding fails, just encode as-is
        encoded_password = quote(password, safe="")

    # Reconstruct URL
    if username:
        return f"redis://{username}:{encoded_password}@{rest}"
    return f"redis://:{encoded_password}@{rest}"
